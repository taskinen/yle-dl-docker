#!/usr/bin/env python3
"""
Lightweight web interface for yle-dl
Streams yle-dl output to browser in real-time via SSE
"""

import os
import io
import pty
import errno
import fcntl
import json
import uuid
import struct
import termios
import subprocess
import threading
import time
from collections import deque
from datetime import datetime, timezone, timedelta
from pathlib import Path
from queue import Queue, Empty
from concurrent.futures import ThreadPoolExecutor
from bottle import Bottle, request, response, template, redirect, TEMPLATE_PATH
from ansi2html import Ansi2HTMLConverter

# Look for templates next to this script, regardless of the working directory.
TEMPLATE_PATH.insert(0, str(Path(__file__).parent / 'templates'))

# Configuration
WORKERS = int(os.environ.get('WORKERS', 3))
JOB_RETENTION_DAYS = 7
MAX_OUTPUT_LINES = 1000  # bounded scrollback per job
# Terminal states a job can no longer leave; shared by cancel and stream logic.
FINAL_STATES = frozenset({'completed', 'failed', 'cancelled'})
OUTPUT_DIR = Path('/out')
# Job metadata is kept outside OUTPUT_DIR so it never pollutes the user's
# mounted download volume. Overridable via JOBS_DIR.
JOBS_DIR = Path(os.environ.get('JOBS_DIR', '/var/lib/yle-dl-web/jobs'))

# Initialize
app = Bottle()
JOBS_DIR.mkdir(parents=True, exist_ok=True)

# ANSI to HTML converter
ansi_conv = Ansi2HTMLConverter(inline=True, scheme='xterm')


class JobManager:
    """Thread-safe job management"""

    def __init__(self):
        self.jobs = {}
        self.lock = threading.Lock()
        self.executor = ThreadPoolExecutor(max_workers=WORKERS)
        self.subscribers = {}  # job_id -> list of queues for SSE
        self.processes = {}    # job_id -> running Popen (for cancellation)
        self.cancelled = set()  # job_ids that were cancelled by the user

    def create_job(self, url):
        """Create a new download job"""
        job_id = str(uuid.uuid4())
        job = {
            'job_id': job_id,
            'url': url,
            'status': 'queued',
            'output_file': None,
            'error': None,
            'start_time': datetime.now(timezone.utc).isoformat(),
            'end_time': None,
            # deque(maxlen=...) bounds scrollback automatically in O(1) — no
            # manual length check or list re-slicing on every append.
            'output_lines': deque(maxlen=MAX_OUTPUT_LINES),
            'progress_line': None  # transient live line from '\r' redraws
        }

        with self.lock:
            self.jobs[job_id] = job
            self.subscribers[job_id] = []

        self._persist_job(job_id)

        # Submit to worker pool
        self.executor.submit(self._worker, job_id)

        return job_id

    def get_job(self, job_id):
        """Get job by ID"""
        with self.lock:
            return self.jobs.get(job_id)

    def update_job(self, job_id, **kwargs):
        """Update job fields"""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].update(kwargs)
                self._persist_job(job_id)

    def _publish(self, job_id, event):
        """Push an event to all subscribers of a job. Caller must hold the lock.

        create_job always seeds self.subscribers[job_id], and the key is never
        removed, so a plain lookup is safe without an existence guard.
        """
        for queue in self.subscribers[job_id]:
            queue.put(event)

    def append_output(self, job_id, line):
        """Append output line and notify subscribers"""
        with self.lock:
            if job_id in self.jobs:
                # deque(maxlen) drops the oldest line automatically.
                self.jobs[job_id]['output_lines'].append(line)
                self._publish(job_id, {'type': 'line', 'line': line})

    def update_progress(self, job_id, line):
        """Update the transient 'live' line (a '\\r' progress redraw).

        Unlike append_output, this is not persisted to history: it represents
        the single terminal line that yle-dl keeps overwriting. Passing None
        clears it. Subscribers replace their current live line in place.
        """
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id]['progress_line'] = line
                self._publish(job_id, {'type': 'progress', 'line': line})

    def notify_status(self, job_id, status):
        """Notify subscribers of status change"""
        with self.lock:
            if job_id in self.jobs:
                self._publish(job_id, {'type': 'status', 'status': status})

    def subscribe(self, job_id):
        """Subscribe to job updates (returns a queue).

        The current history is seeded as the first event under the same lock
        that append_output/update_progress hold when pushing. This makes
        "get the backlog" and "start receiving live events" atomic: a client
        can neither miss a line emitted between the two nor receive one twice.
        """
        queue = Queue()
        with self.lock:
            job = self.jobs.get(job_id)
            if job is not None:
                queue.put({
                    'type': 'snapshot',
                    'lines': list(job['output_lines']),
                    'progress': job['progress_line'],
                })
                self.subscribers[job_id].append(queue)
        return queue

    def unsubscribe(self, job_id, queue):
        """Unsubscribe from job updates"""
        with self.lock:
            if job_id in self.subscribers and queue in self.subscribers[job_id]:
                self.subscribers[job_id].remove(queue)

    def cancel_job(self, job_id):
        """Cancel a queued or running job. Returns True if it was cancellable."""
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job['status'] in FINAL_STATES:
                return False
            # Mark as cancelled so the worker knows this was intentional.
            self.cancelled.add(job_id)
            process = self.processes.get(job_id)

        # Terminate the process outside the lock; the worker thread will
        # observe the non-zero exit and mark the job as cancelled.
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
        else:
            # Job was still queued (no process yet): mark it cancelled now.
            self.update_job(
                job_id,
                status='cancelled',
                end_time=datetime.now(timezone.utc).isoformat()
            )
            self.notify_status(job_id, 'cancelled')
        return True

    @staticmethod
    def _job_json(job):
        """Return a JSON-serializable view of a job (output_lines is a deque)."""
        return {**job, 'output_lines': list(job['output_lines'])}

    def list_jobs(self):
        """List all jobs (JSON-safe)"""
        with self.lock:
            return [self._job_json(job) for job in self.jobs.values()]

    def cleanup_old_jobs(self):
        """Remove job files older than JOB_RETENTION_DAYS"""
        try:
            cutoff = datetime.now(timezone.utc) - timedelta(days=JOB_RETENTION_DAYS)
            for job_file in JOBS_DIR.glob('*.json'):
                try:
                    # Check file modification time
                    mtime = datetime.fromtimestamp(job_file.stat().st_mtime, tz=timezone.utc)
                    if mtime < cutoff:
                        job_file.unlink()
                except Exception as e:
                    print(f'Error cleaning up {job_file}: {e}')
        except Exception as e:
            print(f'Error during job cleanup: {e}')

    def _persist_job(self, job_id):
        """Save job to disk"""
        job = self.jobs.get(job_id)
        if job:
            job_file = JOBS_DIR / f'{job_id}.json'
            with open(job_file, 'w') as f:
                json.dump(self._job_json(job), f, indent=2)

    def _worker(self, job_id):
        """Worker thread that runs yle-dl"""
        job = self.get_job(job_id)
        if not job:
            return

        self.update_job(job_id, status='downloading')
        self.notify_status(job_id, 'downloading')

        master_fd = None
        stream = None
        try:
            # Run yle-dl attached to a pseudo-terminal. yle-dl shells out to
            # wget for direct file downloads, and wget checks isatty(stdout):
            # on a terminal it draws a single-line progress bar redrawn with
            # '\r'; on a plain pipe it falls back to verbose multi-line "dot"
            # output. Giving the child a PTY makes it emit the same clean
            # single-line progress the CLI shows, which the '\r'/'\n' loop
            # below already knows how to render. (ffmpeg, used for streams,
            # writes '\r' progress either way.)
            master_fd, slave_fd = pty.openpty()

            # Disable ONLCR on the slave: without this the tty layer rewrites
            # the child's '\n' into '\r\n', which would leave a stray '\r' on
            # every committed line. With it off the byte stream matches the CLI
            # exactly (bare '\r' for redraws, bare '\n' for committed lines).
            attrs = termios.tcgetattr(slave_fd)
            attrs[1] &= ~termios.ONLCR  # oflag
            termios.tcsetattr(slave_fd, termios.TCSANOW, attrs)

            # Give wget a roomy width so its progress bar isn't cramped.
            fcntl.ioctl(slave_fd, termios.TIOCSWINSZ,
                        struct.pack('HHHH', 24, 120, 0, 0))

            # Pass '--' so the URL is never interpreted as yle-dl option,
            # even if validation is ever relaxed.
            process = subprocess.Popen(
                ['yle-dl', '--', job['url']],
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=str(OUTPUT_DIR),
                close_fds=True
            )
            # The child holds its own copy of the slave; close ours so that
            # reads on the master see EOF once the child exits.
            os.close(slave_fd)

            # Register the process so it can be cancelled. If a cancel arrived
            # while the job was still queued, terminate immediately.
            with self.lock:
                if job_id in self.cancelled:
                    process.terminate()
                self.processes[job_id] = process

            # Read the master end. newline='' preserves lone '\r' instead of
            # letting universal-newline mode translate it to '\n'. yle-dl/wget/
            # ffmpeg redraw progress on one terminal line with '\r'; we mirror
            # that so the web view shows a single updating line, not one per tick.
            stream = io.TextIOWrapper(
                os.fdopen(master_fd, 'rb', buffering=0),
                encoding='utf-8', errors='replace', newline=''
            )

            # Model the terminal's active line. yle-dl redraws progress with
            # '\r' (cursor to column 0, overwrite) and only advances to a new
            # line on '\n'. So '\r'-terminated chunks update a transient "live"
            # line that is never persisted; '\n' commits the line to history.
            # The wrapper yields one chunk per terminator, so a committing chunk
            # already holds the full overwriting text — never concatenate it
            # onto the previous progress text.
            current_line = ''       # content shown on the live (unfinished) line
            progress_active = False  # a '\r' redraw is currently displayed
            try:
                for chunk in stream:
                    if chunk.endswith('\r'):
                        # Progress redraw: update the live line in place.
                        current_line = chunk[:-1]
                        progress_active = True
                        self.update_progress(job_id, self._convert_ansi(current_line))
                    else:
                        # Committed by '\n' (or the final unterminated EOF chunk).
                        # Non-empty text overwrites the live line; a bare newline
                        # commits whatever the live line already held.
                        # A bare newline (empty text) commits whatever the live
                        # line already held; otherwise this chunk's text is the line.
                        # Strip a trailing '\r' too: over a PTY, wget ends its
                        # final progress redraw with '\r' right before the '\n',
                        # yielding a '\r\n' chunk — the '\r' is cursor control,
                        # never content.
                        text = chunk.rstrip('\r\n')
                        committed = text if text else current_line
                        if committed.strip():
                            self.append_output(job_id, self._convert_ansi(committed))
                        if progress_active:
                            # The live line has been finalized; clear the transient.
                            self.update_progress(job_id, None)
                            progress_active = False
                        current_line = ''
            except OSError as e:
                # Reading a PTY master after the child has closed the slave
                # raises EIO on Linux instead of returning EOF. Treat it as a
                # clean end of stream; re-raise anything else.
                if e.errno != errno.EIO:
                    raise

            # Commit any progress text left on the live line at EOF, then clear
            # the transient so the frontend doesn't show it twice.
            if current_line.strip():
                self.append_output(job_id, self._convert_ansi(current_line))
            if progress_active:
                self.update_progress(job_id, None)

            process.wait()

            was_cancelled = job_id in self.cancelled

            # Check result
            if was_cancelled:
                self.update_job(
                    job_id,
                    status='cancelled',
                    end_time=datetime.now(timezone.utc).isoformat()
                )
                self.notify_status(job_id, 'cancelled')
            elif process.returncode == 0:
                self.update_job(
                    job_id,
                    status='completed',
                    end_time=datetime.now(timezone.utc).isoformat()
                )
                self.notify_status(job_id, 'completed')
            else:
                self.update_job(
                    job_id,
                    status='failed',
                    error=f'yle-dl exited with code {process.returncode}',
                    end_time=datetime.now(timezone.utc).isoformat()
                )
                self.notify_status(job_id, 'failed')

        except Exception as e:
            self.update_job(
                job_id,
                status='failed',
                error=str(e),
                end_time=datetime.now(timezone.utc).isoformat()
            )
            self.notify_status(job_id, 'failed')
        finally:
            # Close the PTY master. If the TextIOWrapper was created it owns
            # the fd; otherwise close the raw fd directly. Guard against a
            # double close (e.g. spawn failed before the wrapper existed).
            try:
                if stream is not None:
                    stream.close()
                elif master_fd is not None:
                    os.close(master_fd)
            except OSError:
                pass
            with self.lock:
                self.processes.pop(job_id, None)

    def _convert_ansi(self, line):
        """Convert ANSI codes to HTML"""
        try:
            return ansi_conv.convert(line, full=False)
        except Exception:
            # Fallback to plain text if conversion fails
            return line


# Global job manager
job_manager = JobManager()


# Routes

@app.route('/')
def index():
    """Main page"""
    url_param = request.query.get('url')

    if url_param:
        url_param = url_param.strip()
        if not url_param.startswith('https://'):
            response.status = 400
            return template('error.html',
                            job_id='Invalid URL. Must start with https://')
        # Create job and redirect to status page (relative URL)
        job_id = job_manager.create_job(url_param)
        return redirect(f'status?job_id={job_id}')

    return template('index.html')


@app.route('/status')
def status_page():
    """Status page for a single job, or the all-jobs overview if no job_id."""
    job_id = request.query.get('job_id')

    if not job_id:
        # Overview of all jobs (client renders times in the browser timezone).
        return template('jobs.html')

    job = job_manager.get_job(job_id)

    if not job:
        return template('error.html', job_id=job_id)

    return template('status.html', job_id=job_id, status=job['status'])


@app.route('/stream/<job_id>')
def stream(job_id):
    """SSE stream for job updates"""
    job = job_manager.get_job(job_id)
    if not job:
        response.status = 404
        return {'error': 'Job not found'}

    # Set SSE headers
    response.content_type = 'text/event-stream'
    response.set_header('Cache-Control', 'no-cache')
    response.set_header('X-Accel-Buffering', 'no')

    # Subscribe to job updates
    queue = job_manager.subscribe(job_id)

    def generate():
        try:
            while True:
                # Block until the worker pushes an event, so output reaches the
                # browser with no polling delay. The timeout just lets us send a
                # keepalive and re-check whether the job has finished.
                try:
                    event = queue.get(timeout=15)
                    yield f'data: {json.dumps(event)}\n\n'
                    continue
                except Empty:
                    pass

                # No events for a while: keepalive and check for completion.
                # Only stop once the queue is empty so the final status event
                # is never dropped.
                yield ': keepalive\n\n'
                current_job = job_manager.get_job(job_id)
                if (current_job
                        and current_job['status'] in FINAL_STATES
                        and queue.empty()):
                    break
        finally:
            job_manager.unsubscribe(job_id, queue)

    return generate()


@app.route('/api/job/<job_id>/cancel', method='POST')
def cancel_job_api(job_id):
    """Cancel a running or queued job"""
    job = job_manager.get_job(job_id)
    if not job:
        response.status = 404
        return {'error': 'Job not found'}
    if job_manager.cancel_job(job_id):
        return {'status': 'cancelled'}
    response.status = 409
    return {'error': 'Job is already finished'}


@app.route('/api/jobs')
def list_jobs_api():
    """List all jobs"""
    return {'jobs': job_manager.list_jobs()}


def cleanup_worker():
    """Background thread for periodic job cleanup"""
    while True:
        time.sleep(86400)  # Run once per day
        job_manager.cleanup_old_jobs()


if __name__ == '__main__':
    print('Starting yle-dl Web Interface on port 8080')
    print(f'Workers: {WORKERS}')
    print(f'Job retention: {JOB_RETENTION_DAYS} days')
    print(f'Output directory: {OUTPUT_DIR}')

    # Start cleanup worker
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()

    app.run(host='0.0.0.0', port=8080, server='paste')

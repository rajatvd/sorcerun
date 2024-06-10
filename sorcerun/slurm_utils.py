import subprocess


class Job:
    def __init__(
        self,
        job_id,
    ):
        self.job_id = job_id
        self.job_state = None
        self.duration = None

    def __str__(self):
        return f"Job {self.job_id} is {self.job_state} for {self.duration}"

    def __repr__(self):
        return str(self)

    def update(self):
        # Get the job state
        cmd = f"sacct -j {self.job_id} -o state,elapsed --noheader"
        print(cmd)
        out = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
        self.job_state, self.duration = out.split()


def update_jobs(jobs):
    cmd = f"sacct -j {','.join([str(j.job_id) for j in jobs])} -o state,elapsed --noheader"
    out = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    for job, line in zip(jobs, out.split("\n")):
        job.job_state, job.duration = line.split()


def aggregate_states(jobs):
    states = {}
    for job in jobs:
        if job.job_state not in states:
            states[job.job_state] = 0
        states[job.job_state] += 1
    return states

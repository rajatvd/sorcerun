import subprocess
from collections import OrderedDict
from prettytable import PrettyTable
import time


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
    states = OrderedDict()
    states["PENDING"] = 0
    states["RUNNING"] = 0
    states["COMPLETED"] = 0

    for job in jobs:
        if job.job_state not in states:
            states[job.job_state] = 0
        states[job.job_state] += 1
    return states


def poll_jobs(jobs, poll_interval=10):
    print(f"Polling {len(jobs)} jobs every {poll_interval} seconds\n")

    update_jobs(jobs)
    states = aggregate_states(jobs)
    while states.get("PENDING", 0) + states.get("RUNNING", 0) > 0:
        t = PrettyTable(["Job State", "Count"])
        for state, count in states.items():
            t.add_row([state, count])
        t.align = "l"
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print("-" * 40)
        print(f"Job states at {time_str} :")
        print(t)
        print("-" * 40)

        time.sleep(poll_interval)

        update_jobs(jobs)
        states = aggregate_states(jobs)

    print("All jobs have finished")

import subprocess
from collections import OrderedDict
from prettytable import PrettyTable
import time
from tqdm import tqdm


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
    total = len(jobs)
    print(f"Polling {total} jobs every {poll_interval} seconds\n")

    bar_format = "{desc} -- {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt}"
    update_jobs(jobs)
    time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    launched = tqdm(
        total=total,
        desc=f"Launched  @ {time_str}",
        position=0,
        bar_format=bar_format,
    )
    completed = tqdm(
        total=total,
        desc=f"Completed @ {time_str}",
        position=1,
        bar_format=bar_format,
    )
    states = aggregate_states(jobs)
    first_iter = True
    while states.get("PENDING", 0) + states.get("RUNNING", 0) > 0 or first_iter:
        first_iter = False
        t = PrettyTable(["Job State", "Count"])
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        for state, count in states.items():
            t.add_row([state, count])
            launched.n = states.get("RUNNING", 0) + states.get("COMPLETED", 0)
            launched.desc = f"Launched  @ {time_str}"
            launched.refresh()
            completed.n = states.get("COMPLETED", 0)
            completed.desc = f"Completed @ {time_str}"
            completed.refresh()
        t.align = "l"
        # print("-" * 40)
        # print(f"Job states at {time_str}")
        # print(t)
        # print("-" * 40)

        time.sleep(poll_interval)

        update_jobs(jobs)
        states = aggregate_states(jobs)

    launched.close()
    completed.close()

    print("All jobs have finished")

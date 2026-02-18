import subprocess


def stop_container(container):
    subprocess.run(
        ["docker", "rm", "-f", container],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def start_container(container, image="reddis_xor:latest"):
    subprocess.run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            container,
            "-p", "6380:6379",
            image,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )


def get_peak(container):
    result = subprocess.run(
        [
            "docker",
            "exec",
            container,
            "sh",
            "-c",
            "cat /sys/fs/cgroup/memory.peak",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    return int(result.stdout.strip()) / 1024 / 1024

#!/usr/bin/env python3
"""Stream a puffer run's metrics jsonl (base.wandb=True) to wandb.

Wrapper (live):  wandb_sync.py --project P [--group G] [--name N] -- ./puffer train ...
                 injects --base.wandb=True --base.run_id=<name>, follows the file
Import (post):   wandb_sync.py --project P --file logs/ENV/RUN.jsonl [--name N]
Sweep (live):    wandb_sync.py --project P [--group G] --watch logs/ENV
                 one wandb run per new *.jsonl; a run finishes when its file
                 goes idle for --idle seconds

5.0 CLI is `./puffer train [--section.key=value]` (env compiled in). A leftover
positional ENV (5c) and bare `section.key=value` args are normalized.
"""
import argparse
import configparser
import glob
import json
import os
import subprocess
import sys
import time


MODES = ("train", "eval", "sweep", "match")


def read_config(ini_path):
    cp = configparser.ConfigParser(strict=False)
    try:
        cp.read(ini_path)
        return {f"{s}.{k}": v for s in cp.sections() for k, v in cp[s].items()}
    except Exception:
        return {}


def base_key(configs, key, default):
    cp = configparser.ConfigParser(strict=False)
    cp.read(configs)
    return cp.get("base", key, fallback=default)


def infer_env(cmd):
    for a in cmd:
        if a.startswith("--base.env_name="):
            return a.split("=", 1)[1]
        if a.startswith("base.env_name="):
            return a.split("=", 1)[1]
    saw_mode = False
    for a in cmd[1:]:
        if a in MODES:
            saw_mode = True
            continue
        if saw_mode and not a.startswith("-") and "=" not in a:
            return a
        saw_mode = False
    return None


def normalize_cmd(cmd):
    """5.0 requires --section.key=value; drop a leftover positional ENV."""
    out = []
    drop_env = False
    for a in cmd:
        if a in MODES:
            out.append(a)
            drop_env = True
            continue
        if drop_env:
            drop_env = False
            if not a.startswith("-") and "=" not in a:
                continue
        if "=" in a and not a.startswith("-"):
            out.append("--" + a)
        else:
            out.append(a)
    return out


def wait_jsonl(name, hinted, timeout=120.0):
    if hinted:
        deadline = time.time() + timeout
        while not os.path.exists(hinted):
            if time.time() > deadline:
                return hinted
            time.sleep(0.2)
        return hinted
    deadline = time.time() + timeout
    pattern = os.path.join("logs", "*", f"{name}.jsonl")
    while time.time() < deadline:
        hits = sorted(glob.glob(pattern))
        if hits:
            return hits[0]
        time.sleep(0.2)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", required=True)
    ap.add_argument("--entity", default=None)
    ap.add_argument("--group", default=None)
    ap.add_argument("--name", default=None)
    ap.add_argument("--tags", default=None, help="comma-separated")
    ap.add_argument("--file", default=None, help="import an existing jsonl")
    ap.add_argument("--watch", default=None, help="dir: one wandb run per new jsonl")
    ap.add_argument("--idle", type=float, default=0.0,
                    help="file mode: keep following until idle this long (0 = stop at EOF)")
    ap.add_argument("cmd", nargs="*", help="-- ./puffer train [--section.key=value]")
    args = ap.parse_args()

    if args.watch:
        seen = {}
        try:
            while True:
                for fn in sorted(os.listdir(args.watch)):
                    if fn.endswith(".jsonl") and fn not in seen:
                        fp = os.path.join(args.watch, fn)
                        cmd = [sys.executable, __file__, "--project", args.project,
                               "--file", fp, "--idle", str(args.idle or 180.0)]
                        for flag in ("entity", "group", "tags"):
                            v = getattr(args, flag)
                            if v:
                                cmd += [f"--{flag}", v]
                        print(f"wandb_sync: new trial {fn}")
                        seen[fn] = subprocess.Popen(cmd)
                time.sleep(2.0)
        except KeyboardInterrupt:
            for c in seen.values():
                c.wait()
            return

    child = None
    if args.cmd:
        cmd = normalize_cmd(args.cmd)
        env_name = infer_env(args.cmd)
        name = args.name or (f"{env_name}_{int(time.time())}" if env_name
                             else f"run_{int(time.time())}")
        log_dir = base_key(["config/default.ini"], "log_dir", "logs")
        if env_name:
            hinted = os.path.join(log_dir, env_name, f"{name}.jsonl")
            if os.path.exists(hinted):
                os.remove(hinted)
        else:
            hinted = None
        child = subprocess.Popen(
            cmd + ["--base.wandb=True", f"--base.run_id={name}"])
        path = wait_jsonl(name, hinted)
        if path is None:
            print("wandb_sync: timed out waiting for jsonl", file=sys.stderr)
            rc = child.wait()
            sys.exit(rc or 1)
    else:
        assert args.file, "need --file or a command after --"
        path = args.file
        name = args.name or os.path.basename(path)[:-len(".jsonl")]

    import wandb
    run = wandb.init(
        project=args.project, entity=args.entity, group=args.group, name=name,
        tags=args.tags.split(",") if args.tags else None)
    wandb.define_metric("agent_steps")
    wandb.define_metric("*", step_metric="agent_steps")

    f = None
    config_sent = False
    last = None
    rows = 0
    last_data = time.time()
    while True:
        if f is None:
            if os.path.exists(path):
                f = open(path)
            elif child is not None and child.poll() is not None:
                break
            else:
                time.sleep(0.5)
                continue
        line = f.readline()
        if not line:
            if child is not None:
                if child.poll() is not None:
                    break
            elif args.idle <= 0 or time.time() - last_data > args.idle:
                break
            time.sleep(1.0)
            continue
        if not line.endswith("\n"):  # partial write; rewind and retry
            f.seek(f.tell() - len(line))
            time.sleep(0.2)
            continue
        if not config_sent:
            cfg = read_config(path[:-len(".jsonl")] + ".ini")
            if cfg:
                run.config.update(cfg)
            config_sent = True
        try:
            last = json.loads(line)
        except json.JSONDecodeError:
            continue
        wandb.log(last)
        rows += 1
        last_data = time.time()

    if last:
        run.summary.update(last)
    rc = child.wait() if child is not None else 0
    print(f"wandb_sync: {rows} rows -> {run.url}")
    run.finish(exit_code=rc)
    sys.exit(rc)


if __name__ == "__main__":
    main()

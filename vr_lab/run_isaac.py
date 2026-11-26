"""Open the lab in Isaac Sim 5.x and receive local VR pose packets."""
import argparse
import json
from pathlib import Path
import socket
import sys

from isaacsim import SimulationApp

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--frames", type=int, default=0, help="Exit after N updates (0 runs until closed)")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    app = SimulationApp({"headless": args.headless})
    try:
        import omni.timeline
        import omni.usd

        from pose import apply_pose, REST_POSE

        context = omni.usd.get_context()
        scene = Path(__file__).with_name("lab.usda").resolve()
        if not context.open_stage(str(scene)):
            raise RuntimeError(f"Could not open {scene}")
        while context.is_stage_loading():
            app.update()
        stage = context.get_stage()
        if stage is None:
            raise RuntimeError("Isaac Sim did not open the USD stage")
        # Store live transforms in the session layer so the rest pose stays on disk.
        stage.SetEditTarget(stage.GetSessionLayer())
        apply_pose(stage, REST_POSE)

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as receiver:
            receiver.bind(("127.0.0.1", args.port))
            receiver.setblocking(False)
            omni.timeline.get_timeline_interface().play()
            print(f"Lab ready. Listening on 127.0.0.1:{args.port}", flush=True)
            frames = 0
            while app.is_running() and (args.frames == 0 or frames < args.frames):
                # Bound input processing to keep stage updates responsive.
                for _ in range(32):
                    try:
                        data = receiver.recv(4096)
                    except BlockingIOError:
                        break
                    try:
                        apply_pose(stage, json.loads(data))
                    except (UnicodeError, ValueError) as error:
                        print(f"Invalid pose: {error}", file=sys.stderr)
                app.update()
                frames += 1
    finally:
        app.close()

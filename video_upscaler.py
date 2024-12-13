import os
import subprocess
import math
import json
from pathlib import Path
import shutil

STATE_FILE = "progress.json"
LAST_OPERATION_FILE = "last_operation.json"

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_last_operation(data):
    with open(LAST_OPERATION_FILE, 'w') as f:
        json.dump(data, f)

def load_last_operation():
    if os.path.exists(LAST_OPERATION_FILE):
        with open(LAST_OPERATION_FILE, 'r') as f:
            return json.load(f)
    return {}

def run_command(command):
    print(f"Running: {command}")
    subprocess.run(command, shell=True, check=True)

def extract_frames(video_path, output_folder):
    os.makedirs(output_folder, exist_ok=True)
    run_command(f"ffmpeg -i {video_path} -qscale:v 2 {output_folder}/frame_%04d.png")

def rebuild_video(frames_folder, output_video, fps):
    run_command(f"ffmpeg -framerate {fps} -i {frames_folder}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p {output_video}")

def upscale_frame(input_frame, scale_factor, model, use_cpu):
    """
    Upscales a single frame directly using the specified scale factor.
    """
    cpu_flag = "-g -1" if use_cpu else ""
    valid_scales = [2, 4, 8, 16, 32]
    if scale_factor in valid_scales:
        upscale_cmd = f"upscaler2x -i {input_frame} -o {input_frame.replace('frames', 'upscaled_frames')} -v -n -1 -s {scale_factor} -j 3:7:3 -m ~/.upscaler_models/{model} {cpu_flag}"
        run_command(upscale_cmd)
    else:
        raise ValueError(f"Unsupported scale factor: {scale_factor}. Valid options are {valid_scales}.")

def upscale_chunk(chunk_folder, scale_factor, model, state, use_cpu):
    """
    Upscales all frames in a chunk directly by the specified scale factor.
    """
    frames_folder = os.path.join(chunk_folder, "frames")
    upscaled_folder = os.path.join(chunk_folder, "upscaled_frames")
    os.makedirs(upscaled_folder, exist_ok=True)

    frames = sorted(Path(frames_folder).glob("*.png"))
    completed_frames = state.get("completed_frames", [])

    for i, frame in enumerate(frames):
        frame_name = str(frame)
        if frame_name in completed_frames:
            print(f"Skipping already upscaled frame: {frame_name}")
            continue
        print(f"Upscaling frame {i + 1}/{len(frames)} with scale factor {scale_factor}")
        upscale_frame(frame_name, scale_factor, model, use_cpu)
        completed_frames.append(frame_name)
        state["completed_frames"] = completed_frames
        save_state(state)

    return upscaled_folder

def split_video(input_video, chunk_time, resume=False):
    output_chunks = []
    chunks_folder = "temp/chunks"
    if resume and os.path.exists(chunks_folder):
        print("Skipping video splitting as chunks already exist.")
        return sorted(Path(chunks_folder).glob("*.mp4"))

    duration_command = f"ffmpeg -i {input_video} 2>&1 | grep Duration"
    result = subprocess.run(duration_command, shell=True, capture_output=True, text=True)
    duration_str = result.stdout.split("Duration: ")[1].split(",")[0]
    hours, minutes, seconds = duration_str.split(":")
    seconds = float(seconds)
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + seconds
    num_chunks = math.ceil(total_seconds / chunk_time)

    os.makedirs(chunks_folder, exist_ok=True)

    for i in range(num_chunks):
        chunk_name = f"chunk_{i+1}.mp4"
        chunk_path = os.path.join(chunks_folder, chunk_name)
        start_time = i * chunk_time
        run_command(f"ffmpeg -i {input_video} -ss {start_time} -t {chunk_time} -c copy {chunk_path}")
        output_chunks.append(chunk_path)

    return output_chunks

def merge_upscaled_chunks(chunk_files, output_file, original_video):
    list_file = "chunk_list.txt"
    with open(list_file, "w") as f:
        for chunk in chunk_files:
            f.write(f"file '{chunk}'\n")
    merge_command = (
        f"ffmpeg -f concat -safe 0 -i {list_file} -i {original_video} "
        f"-c:v copy -c:a copy -map 0:v:0 -map 1:a? -map 1:s? {output_file}"
    )
    run_command(merge_command)
    os.remove(list_file)

def process_video(input_video, output_video, scale_factor, chunk_time, model, resume, use_cpu):
    temp_folder = "temp"
    os.makedirs(temp_folder, exist_ok=True)

    state = load_state() if resume else {"completed_chunks": [], "completed_frames": []}

    if resume:
        last_operation = load_last_operation()
        if not last_operation:
            print("No previous operation found to resume.")
            return
        input_video = last_operation["input_video"]
        output_video = last_operation["output_video"]
        scale_factor = last_operation["scale_factor"]
        chunk_time = last_operation["chunk_time"]
        model = last_operation["model"]
        use_cpu = last_operation["use_cpu"]
    else:
        save_last_operation({
            "input_video": input_video,
            "output_video": output_video,
            "scale_factor": scale_factor,
            "chunk_time": chunk_time,
            "model": model,
            "use_cpu": use_cpu
        })

    print("Splitting video...")
    chunks = split_video(input_video, chunk_time, resume=resume)
    fps_command = f"ffprobe -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate {input_video}"
    fps_result = subprocess.run(fps_command, shell=True, capture_output=True, text=True)
    fps = eval(fps_result.stdout.strip())

    print("Processing each chunk...")
    upscaled_chunks = []
    for chunk_path in chunks:
        chunk_name = os.path.splitext(os.path.basename(chunk_path))[0]
        if chunk_name in state.get("completed_chunks", []):
            print(f"Skipping already processed chunk: {chunk_name}")
            continue
        chunk_folder = os.path.join(temp_folder, "chunks", chunk_name)
        frames_folder = os.path.join(chunk_folder, "frames")
        os.makedirs(chunk_folder, exist_ok=True)

        print(f"Extracting frames for {chunk_name}...")
        extract_frames(chunk_path, frames_folder)

        print(f"Upscaling frames for {chunk_name}...")
        final_upscaled_folder = upscale_chunk(chunk_folder, scale_factor, model, state, use_cpu)

        upscaled_video = os.path.join(temp_folder, "chunks", f"upscaled_{chunk_name}.mp4")
        print(f"Rebuilding upscaled chunk {chunk_name}...")
        rebuild_video(final_upscaled_folder, upscaled_video, fps)
        upscaled_chunks.append(upscaled_video)

        print(f"Removing chunk folder: {chunk_folder}")
        shutil.rmtree(chunk_folder)

        state["completed_chunks"].append(chunk_name)
        save_state(state)

    print("Merging upscaled chunks into final video...")
    merge_upscaled_chunks(upscaled_chunks, output_video, input_video)

    print(f"Cleaning up temporary files...")
    shutil.rmtree(temp_folder)
    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    save_last_operation({
        "input_video": input_video,
        "output_video": output_video,
        "scale_factor": scale_factor,
        "chunk_time": chunk_time,
        "model": model,
        "use_cpu": use_cpu
    })

    print(f"Upscaled video saved as {output_video}")

if __name__ == "__main__":
    import sys

    def print_usage():
        print("""
Usage:
    python video_upscaler.py resume
        Resume the last operation.

    python video_upscaler.py <input_video> <output_video> <scale_factor> <chunk_time> <model> [cpu|gpu]
        Upscale a video with the specified parameters:
            <input_video>    Path to the input video file.
            <output_video>   Path to save the output video.
            <scale_factor>   Upscaling factor (2/4/8/16/32).
            <chunk_time>     Chunk length in seconds.
            <model>          Upscaling model:
                               models-upconv_7_anime_style_art_rgb
                               models-upconv_7_photo
                               models-cunet
            [cpu|gpu]        Optional. Use 'cpu' to process on CPU, otherwise 'gpu' is assumed.

Examples:
    python video_upscaler.py input.mp4 output.mp4 2 10 models-cunet gpu
    python video_upscaler.py input.mp4 output.mp4 4 15 models-upconv_7_photo cpu
""")

    if len(sys.argv) == 2 and sys.argv[1] == "resume":
        process_video(None, None, None, None, None, True, None)
    elif len(sys.argv) in {6, 7}:
        input_video = sys.argv[1]
        output_video = sys.argv[2]
        scale_factor = int(sys.argv[3])
        chunk_time = int(sys.argv[4])
        model = sys.argv[5]

        if scale_factor not in [2, 4, 8, 16, 32]:
    	    print("Error: Scale factor must be one of 2, 4, 8, 16, or 32.")
    	    print_usage()
    	    sys.exit(1)

        valid_models = ["models-upconv_7_anime_style_art_rgb", "models-upconv_7_photo", "models-cunet"]
        if model not in valid_models:
            print(f"Error: Invalid model '{model}'. Valid options are: {', '.join(valid_models)}")
            print_usage()
            sys.exit(1)

        use_cpu = False
        if len(sys.argv) == 7:
            if sys.argv[6] == "cpu":
                use_cpu = True
            elif sys.argv[6] != "gpu":
                print(f"Error: Invalid processing option '{sys.argv[6]}'. Use 'cpu' or 'gpu'.")
                print_usage()
                sys.exit(1)

        process_video(input_video, output_video, scale_factor, chunk_time, model, False, use_cpu)
    else:
        print("Error: Invalid arguments.")
        print_usage()
        sys.exit(1)

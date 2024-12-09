import os
import subprocess
import math
from pathlib import Path
import shutil

def run_command(command):
    """Runs a shell command."""
    print(f"Running: {command}")
    subprocess.run(command, shell=True, check=True)

def extract_frames(video_path, output_folder):
    """Extracts frames from a video."""
    os.makedirs(output_folder, exist_ok=True)
    run_command(f"ffmpeg -i {video_path} -qscale:v 2 {output_folder}/frame_%04d.png")

def rebuild_video(frames_folder, output_video, fps):
    """Rebuilds a video from frames."""
    run_command(f"ffmpeg -framerate {fps} -i {frames_folder}/frame_%04d.png -c:v libx264 -pix_fmt yuv420p {output_video}")

def upscale_frame(input_frame, scale_factor, model):
    """Upscales a single frame with the specified model."""
    if scale_factor == 2:
        upscale_cmd = f"upscaler2x -i {input_frame} -o {input_frame.replace('frames', 'upscaled_frames')} -v -n -1 -s 2 -m ~/.upscaler_models/{model}"
        run_command(upscale_cmd)
    elif scale_factor == 4:
        first_upscaled = input_frame.replace('frames', 'upscaled_frames')
        upscale_cmd = f"upscaler2x -i {input_frame} -o {first_upscaled} -v -n -1 -s 2 -m ~/.upscaler_models/{model}"
        run_command(upscale_cmd)
        second_upscaled = first_upscaled.replace('upscaled_frames', 'upscaled_frames_2x')
        upscale_cmd = f"upscaler2x -i {first_upscaled} -o {second_upscaled} -v -n -1 -s 2 -m ~/.upscaler_models/{model}"
        run_command(upscale_cmd)

def upscale_chunk(chunk_folder, scale_factor, model):
    """Upscales all frames in a chunk with the specified model."""
    frames_folder = os.path.join(chunk_folder, "frames")
    upscaled_folder = os.path.join(chunk_folder, "upscaled_frames")
    os.makedirs(upscaled_folder, exist_ok=True)
    
    if scale_factor == 4:
        second_upscaled_folder = os.path.join(chunk_folder, "upscaled_frames_2x")
        os.makedirs(second_upscaled_folder, exist_ok=True)
    
    frames = sorted(Path(frames_folder).glob("*.png"))
    for i, frame in enumerate(frames):
        print(f"Upscaling frame {i + 1}/{len(frames)}")
        upscale_frame(str(frame), scale_factor, model)

    final_upscaled_folder = second_upscaled_folder if scale_factor == 4 else upscaled_folder

    return final_upscaled_folder

def split_video(input_video, chunk_time):
    """Splits the video into chunks."""
    output_chunks = []
    duration_command = f"ffmpeg -i {input_video} 2>&1 | grep Duration"
    result = subprocess.run(duration_command, shell=True, capture_output=True, text=True)
    duration_str = result.stdout.split("Duration: ")[1].split(",")[0]
    hours, minutes, seconds = duration_str.split(":")
    seconds = float(seconds)
    total_seconds = int(hours) * 3600 + int(minutes) * 60 + seconds
    num_chunks = math.ceil(total_seconds / chunk_time)
    
    os.makedirs("temp/chunks", exist_ok=True)
    
    for i in range(num_chunks):
        chunk_name = f"chunk_{i+1}.mp4"
        chunk_path = os.path.join("temp/chunks", chunk_name)
        start_time = i * chunk_time
        run_command(f"ffmpeg -i {input_video} -ss {start_time} -t {chunk_time} -c copy {chunk_path}")
        output_chunks.append(chunk_path)
    
    return output_chunks

def merge_upscaled_chunks(chunk_files, output_file, original_video):
    """Merges upscaled chunks into a single video, including audio and subtitles."""
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

def process_video(input_video, output_video, scale_factor, chunk_time, model):
    """Main function to process the video."""
    temp_folder = "temp"
    os.makedirs(temp_folder, exist_ok=True)

    print("Splitting video...")
    chunks = split_video(input_video, chunk_time)
    fps_command = f"ffprobe -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate {input_video}"
    fps_result = subprocess.run(fps_command, shell=True, capture_output=True, text=True)
    fps = eval(fps_result.stdout.strip())

    print("Processing each chunk...")
    upscaled_chunks = []
    for chunk_path in chunks:
        chunk_name = os.path.splitext(os.path.basename(chunk_path))[0]
        chunk_folder = os.path.join(temp_folder, "chunks", chunk_name)
        frames_folder = os.path.join(chunk_folder, "frames")
        os.makedirs(chunk_folder, exist_ok=True)

        print(f"Extracting frames for {chunk_name}...")
        extract_frames(chunk_path, frames_folder)

        print(f"Upscaling frames for {chunk_name}...")
        final_upscaled_folder = upscale_chunk(chunk_folder, scale_factor, model)

        upscaled_video = os.path.join(temp_folder, "chunks", f"upscaled_{chunk_name}.mp4")
        print(f"Rebuilding upscaled chunk {chunk_name}...")
        rebuild_video(final_upscaled_folder, upscaled_video, fps)
        upscaled_chunks.append(upscaled_video)

        print(f"Removing chunk folder: {chunk_folder}")
        shutil.rmtree(chunk_folder)

    print("Merging upscaled chunks into final video...")
    merge_upscaled_chunks(upscaled_chunks, output_video, input_video)

    print(f"Cleaning up temporary files...")
    shutil.rmtree(temp_folder)
    print(f"Upscaled video saved as {output_video}")

def print_help():
    """Prints help information about the script."""
    help_text = """
    Usage: python video_upscaler.py input.mp4 output.mp4 scale_factor chunk_time [model]
    
    Arguments:
        input.mp4       Input video file
        output.mp4      Output video file
        scale_factor    Upscaling factor (2 or 4)
        chunk_time      Duration of each chunk in seconds
        model           (Optional) Waifu2x model to use. Defaults to 'models-cunet'.
                        Available models:
                        - models-upconv_7_anime_style_art_rgb
                        - models-upconv_7_photo
                        - models-cunet

    Example:
        python video_upscaler.py input.mp4 output.mp4 2 60 models-cunet
        python video_upscaler.py input.mp4 output.mp4 4 120
    """
    print(help_text)

if __name__ == "__main__":
    import sys
    if "--help" in sys.argv:
        print_help()
        sys.exit(0)

    if len(sys.argv) < 5 or len(sys.argv) > 6:
        print_help()
        sys.exit(1)
    
    input_video = sys.argv[1]
    output_video = sys.argv[2]
    scale_factor = int(sys.argv[3])
    chunk_time = int(sys.argv[4])
    model = sys.argv[5] if len(sys.argv) == 6 else "models-cunet"

    if model not in ["models-upconv_7_anime_style_art_rgb", "models-upconv_7_photo", "models-cunet"]:
        print(f"Invalid model '{model}'. Valid options are: models-upconv_7_anime_style_art_rgb, models-upconv_7_photo, models-cunet")
        sys.exit(1)

    process_video(input_video, output_video, scale_factor, chunk_time, model)

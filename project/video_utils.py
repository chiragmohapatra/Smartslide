# Using decord to save frame is much faster than openCV
# Check this link for more info https://medium.com/@haydenfaulkner/extracting-frames-fast-from-a-video-using-opencv-and-python-73b9b7dc9661
# Credits to Hayden Faulkner

import os
import cv2  # still used to save images out
import numpy as np
from decord import VideoReader
from decord import cpu, gpu
import utils
import pytesseract

PROCESSED_FILES_DIR = "project/testing/"


def extract_frames(video_path, frames_dir, overwrite=False, start=-1, end=-1, every=30):
    """
    Extract frames from a video using decord's VideoReader
    :param video_path: path of the video
    :param frames_dir: the directory to save the frames
    :param overwrite: to overwrite frames that already exist?
    :param start: start frame
    :param end: end frame
    :param every: frame spacing
    :return: count of images saved
    """

    # make the paths OS (Windows) compatible
    video_path = os.path.normpath(video_path)
    # make the paths OS (Windows) compatible
    frames_dir = os.path.normpath(frames_dir)

    # get the video path and filename from the path
    video_dir, video_filename = os.path.split(video_path)

    assert os.path.exists(video_path)  # assert the video file exists

    # load the VideoReader
    # can set to cpu or gpu .. ctx=gpu(0)
    vr = VideoReader(video_path, ctx=cpu(0))

    if start < 0:  # if start isn't specified lets assume 0
        start = 0
    if end < 0:  # if end isn't specified assume the end of the video
        end = len(vr)

    frames_list = list(range(start, end, every))
    saved_count = 0

    # this is faster for every > 25 frames and can fit in memory
    if every > 25 and len(frames_list) < 1000:
        frames = vr.get_batch(frames_list).asnumpy()

        # lets loop through the frames until the end
        for index, frame in zip(frames_list, frames):
            save_path = os.path.join(frames_dir, "{:010d}.jpg".format(
                index))  # create the save path
            print(f"frame {index} saved")
            # if it doesn't exist or we want to overwrite anyways
            if not os.path.exists(save_path) or overwrite:
                # save the extracted image
                cv2.imwrite(save_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
                saved_count += 1  # increment our counter by one

    else:  # this is faster for every <25 and consumes small memory
        for index in range(start, end):  # lets loop through the frames until the end
            if index % every == 0:  # if this is a frame we want to write out based on the 'every' argument
                frame = vr[index]  # read an image from the capture
                save_path = os.path.join(frames_dir, "{:010d}.jpg".format(
                    index))  # create the save path
                print(f"frame {index} saved")
                # if it doesn't exist or we want to overwrite anyways
                if not os.path.exists(save_path) or overwrite:
                    # save the extracted image
                    cv2.imwrite(save_path, cv2.cvtColor(
                        frame.asnumpy(), cv2.COLOR_RGB2BGR))
                    saved_count += 1  # increment our counter by one

    return saved_count  # and return the count of the images we saved


def video_to_frames(video_path, frames_dir, overwrite=False, every=1):
    """
    Extracts the frames from a video
    :param video_path: path to the video
    :param frames_dir: directory to save the frames
    :param overwrite: overwrite frames if they exist?
    :param every: extract every this many frames
    :return: path to the directory where the frames were saved, or None if fails
    """

    # make the paths OS (Windows) compatible
    video_path = os.path.normpath(video_path)
    # make the paths OS (Windows) compatible
    frames_dir = os.path.normpath(frames_dir)

    # get the video path and filename from the path
    video_dir, video_filename = os.path.split(video_path)

    # make directory to save frames, its a sub dir in the frames_dir with the video name
    os.makedirs(os.path.join(frames_dir), exist_ok=True)

    print("Extracting frames from {}".format(video_filename))

    # let's now extract the frames
    extract_frames(video_path, frames_dir, every=every)

    # when done return the directory containing the frames
    return os.path.join(frames_dir)


def seperate_into_slides(pdf_file_path, video_file_path, user_id, project_id):
    """Give fraction match between 2 images using SURF and FLANN
    Parameters
    ----------
    pdf_file_path: path of the pdf file
    video_file_path: path of the video file
    user_id: id of the user calling this function. This comes from webapp logged in user
    project_id: id of the project user is working with. This comes from webapp project id that logged in user is currently working on
    Returns
    -------
    int,
        returns array of dictionary ({
            "slide_no",
            "slide_text": text generated using ocr of tessaract, 
            "image_path": path of image (pdf screenshot) of this slide, 
            "video_frame_matched": video frame number matched with this frame, 
            "video_frame_timeframe_match: time stamp in seconds of frame of video that matched with this slide,
            "subtitle": subtitle, 
            "audio_path": path of audio file for this slide
        }) 
    """
    pdf_out_dir = os.path.join(PROCESSED_FILES_DIR, user_id, project_id, "pdf_pages")
    # utils.convert_pdf_to_images(pdf_file_path, out_dir=pdf_out_dir, save_pages=True)
    video_frames_dir = os.path.join(PROCESSED_FILES_DIR, user_id, project_id, "video_frames")
    # video_to_frames(video_path=video_file_path, frames_dir=video_frames_dir, overwrite=True, every=60)

    contrast = cv2.imread("images/jp_gates_contrast.png")
    pdf_frame_texts = []
    for pdf_file_name in os.listdir(pdf_out_dir):
        if pdf_file_name.endswith(".jpg"):
            image_path = os.path.join(pdf_out_dir, pdf_file_name)
            img = cv2.imread(image_path)
            img = cv2.resize(img, (500, 500))
            pdf_frame_texts.append((int(os.path.splitext(pdf_file_name)[0]), pytesseract.image_to_string(img), image_path))

    video_frames_texts = []
    i = 0
    for video_frame_filename in os.listdir(video_frames_dir):
        if video_frame_filename.endswith(".jpg"):
            if (i == 10): break
            image_path = os.path.join(video_frames_dir, video_frame_filename)
            img = cv2.imread(image_path)
            img = cv2.resize(img, (500, 500))
            video_frames_texts.append((int(os.path.splitext(video_frame_filename)[0]), pytesseract.image_to_string(img)))
            i += 1

    pdf_frame_texts.sort()
    video_frames_texts.sort()

    assert len(pdf_frame_texts) > 0
    assert len(video_frames_texts) > 0

    matched = []
    for slide_no, pdf_frame_text, _ in pdf_frame_texts:
        all_comparision = []
        for frame_index, video_frame_text in video_frames_texts:
            s = utils.fraction_match_texts(pdf_frame_text, video_frame_text)
            all_comparision.append((frame_index, s))
            # print(f"slide_no {slide_no}, frame_index {frame_index}, match {s}")
        
        maxs = -1
        for _, s in all_comparision:
            maxs = max(maxs, s)
        
        best_matched = (-1, -1)
        for i in range(0, len(all_comparision)):
            frame_index, s = all_comparision[i]
            if s >= 0.95*(maxs):
                best_matched = (frame_index, s)
                break
            last_s = s

        assert best_matched[0] != -1
        
        print(f"slide_no {slide_no}, video_frame {best_matched[0]}")
        matched.append(best_matched[0])
    

    # {
    # slide_no:,
    # subtitles:,
    # image_path:,
    # audio_path:
    # }

    all_slides_data = []
    for i in range(0, len(pdf_frame_texts)):
        slide_no, slide_text, image_path = pdf_frame_texts[i]
        all_slides_data.append({"slide_no": slide_no+1, "slide_text": slide_text, "image_path": image_path, "video_frame_matched": matched[slide_no], "video_matched_frame_time": utils.get_seconds_from_frame_no(matched[slide_no], video_file_path)})

    times = []
    for i in range(0, len(all_slides_data)):
        if (i == len(all_slides_data)-1):
            times.append((all_slides_data[i]["video_matched_frame_time"], all_slides_data[i]["video_matched_frame_time"]+100000))
        else:
            times.append((all_slides_data[i]["video_matched_frame_time"], all_slides_data[i+1]["video_matched_frame_time"]))

    subs_and_audios = generate_subs(video_file_path , times)
    
    audio_dir = os.path.join(PROCESSED_FILES_DIR, user_id, project_id, "audios")
    for i in range(0, len(all_slides_data)):
        all_slides_data[i]["subtitle"] = subs_and_audios[i][0]
        old_audio_path = subs_and_audios[i][1]
        new_audio_path = os.path.join(audio_dir, slide_no+".mp3")
        os.rename(old_audio_path, new_audio_path)
        all_slides_data[i]["audio_path"] = new_audio_path

    return all_slides_data


if __name__ == '__main__':
    # test it
    # video_to_frames(video_path='project/testing/lecture.mp4', frames_dir='project/testing/extracted_frames', overwrite=True, every=60)
    seperate_into_slides("project/testing/lecture.pdf", "project/testing/lecture.mp4", "0", "0")
import os
import cv2
import numpy as np
from pdf2image import convert_from_path
from pdf2image.generators import threadsafe
from skimage.metrics import structural_similarity as ssim
from skimage import exposure
from sklearn.feature_extraction.text import TfidfVectorizer

def convert_pdf_to_images(pdf_file, out_dir=None, save_pages=False):
    pages = convert_from_path(pdf_file, 500)
    # print(type(pages[0]))
    # Saving the pages
    if save_pages:
        i = 0
        os.makedirs(os.path.join(out_dir), exist_ok=True)
        for page in pages:
            page.save(os.path.join(out_dir, str(i) + ".jpg"), "JPEG")
            i += 1
    return pages

# pdf_file = './data/sample.pdf'
# pages = convert_pdf_to_images(pdf_file, "data/saved", True)

def fraction_match_texts(text_a, text_b):
    text_a = "af " + text_a
    text_b = "af " + text_b
    corpus = [text_a, text_b]
    vect = TfidfVectorizer(min_df=1)
    tfidf = vect.fit_transform(corpus)
    pairwise_similarity = tfidf * tfidf.T
    return pairwise_similarity.toarray()[0][1]     

def fraction_match_images(image_a, image_b):
	# compute the structural similarity
	# returns 0 to 1 depending on percentage match of images
    # s = ssim(image_a, image_b, multichannel = True)
    # s = SIFT_match(imageA, imageB)
	# print("SSIM: %.2f" % (s))
    return ocr_matching(image_a, image_b)

def ocr_matching(image_a, image_b):
    corpus = [pytesseract.image_to_string(image_a), pytesseract.image_to_string(image_b)]
    print(corpus[0])
    print(corpus[1])
    vect = TfidfVectorizer(min_df=1)
    tfidf = vect.fit_transform(corpus)
    pairwise_similarity = tfidf * tfidf.T
    return pairwise_similarity.toarray()[0][1]                                                                                                                                                                                                            


def ssim_matching(imageA, imageB):
    s = ssim(imageA, imageB, multichannel = True)
    return s

def match_using_histogram(imageA, imageB):
    multi = True if imageA.shape[-1] > 1 else False
    matched = exposure.match_histograms(imageA, imageB, multichannel=multi)
    return matched

# From our previous project - ImageLocalisation - DISA 2019 (Vishal Singh, Vishal Bindal, Sushant Sondhi)
def SIFT_match(img1, img2, hessianThreshold: int = 400, ratio_thresh: float = 0.7, symmetry_match: bool = True, show_image: bool = False):
    """Give fraction match between 2 images using SURF and FLANN
    Parameters
    ----------
    img1 : Open CV image format,
    img2 : Open CV image format,
    hessianThreshold: Number of ORB points to consider in a image,
    ratio_thresh: (b/w 0 to 1) lower the number more serious the matching
    symmetry_match:
    Returns
    -------
    float,
        returns a number from 0 to 1 depending on percentage match and returns -1 if any of the parameter is None
    """
    if img1 is None or img2 is None:
        raise Exception("img1 or img2 can't be none")

    if ratio_thresh > 1 or ratio_thresh < 0:
        raise Exception("ratio_thresh not between 0 to 1")

    detector = cv2.SIFT().create(hessianThreshold)
    keypoints1, descriptors1 = detector.detectAndCompute(img1, None)
    keypoints2, descriptors2 = detector.detectAndCompute(img2, None)

    a1 = len(keypoints1)
    b1 = len(keypoints2)

    if a1 < 2 or b1 < 2:
        return 0

    matcher = cv2.DescriptorMatcher_create(cv2.DescriptorMatcher_FLANNBASED)
    knn_matches = matcher.knnMatch(descriptors1, descriptors2, 2)
    good_matches = []
    for m, n in knn_matches:
        if m.distance < ratio_thresh * n.distance:
            good_matches.append(m)
    c1 = len(good_matches)

    if (show_image):
        img3 = np.empty((max(img1.shape[0], img2.shape[0]), img1.shape[1] + img2.shape[1], 3), dtype=np.uint8)
        cv2.drawMatches(
            img1, keypoints1, img2, keypoints2, good_matches, outImg=img3, matchColor=None, flags=2)
        if img3 is not None:
            cv2.namedWindow("matches", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("matches", 1600, 1600)
            cv2.imshow("matches", img3)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    if symmetry_match:
        knn_matches = matcher.knnMatch(descriptors2, descriptors1, 2)
        good_matches = []
        for m, n in knn_matches:
            if m.distance < ratio_thresh * n.distance:
                good_matches.append(m)
        c2 = len(good_matches)

        if (show_image):
            img3 = np.empty((max(img1.shape[0], img2.shape[0]), img1.shape[1] + img2.shape[1], 3), dtype=np.uint8)
            cv2.drawMatches(
                img2, keypoints2, img1, keypoints1, good_matches, outImg=img3, matchColor=None, flags=2)
            if img3 is not None:
                cv2.namedWindow("matches", cv2.WINDOW_NORMAL)
                cv2.resizeWindow("matches", 1600, 1600)
                cv2.imshow("matches", img3)
                cv2.waitKey(0)
                cv2.destroyAllWindows()

        # print(a1,"a1", b1,"b1", c1, "c1", c2, "c2")
        fraction = (c1 + c2) / (a1 + b1)
        return fraction

    fraction = (2.0 * c1) / (a1 + b1)
    if fraction > 1:
        fraction = 1
    # fraction can be greater than one in blur images because we are multiplying fraction with 2
    return fraction

def get_fps_video(video_path: str):
    """Give fraction match between 2 images using SURF and FLANN
    Parameters
    ----------
    video_path: path of the video file
    Returns
    -------
    int,
        returns frames per second in video
    """
    video = cv2.VideoCapture(video_path)
    # Find OpenCV version
    (major_ver, minor_ver, subminor_ver) = (cv2.__version__).split('.')
    if int(major_ver)  < 3 :
        fps = video.get(cv2.cv.CV_CAP_PROP_FPS)
    else :
        fps = video.get(cv2.CAP_PROP_FPS)
    video.release()
    return fps

def get_seconds_from_frame_no(frame_no:int, video_path: str):
    fps = get_fps_video(video_path)
    return int(frame_no/fps)
from utils import *
from pathlib import Path
from rfdetr import RFDETRMedium

def main():
    project_dir = Path.cwd()
    print(project_dir)
    while True:
        file = input('Choose an image file:') + '.jpg'
        img = cv2.imread(project_dir / "notebooks" / "game_opera_side" / file)
        try:
            img = cv2.imread(project_dir / "notebooks" / "game_opera_side" / file)
            print(f"{img} found!")
            break
        except:
            print(f"{file} not found. Please choose a different image file.")
    blur = preprocess(img)
    canny = autocanny(blur)
    dilated = dilate (canny)
    points = find_contour(dilated)
    corners = find_corners(points)
    warped, M_inv = warp(img, corners)
    blur = preprocess(warped)
    canny = autocanny(blur)
    closed = close(canny)
    lines = hough_lines(closed)
    h, v = sort_lines(lines)
    intersections = find_intersections(h, v)
    clustered_points = cluster_intersections(intersections)
    corners = find_corners(clustered_points)
    squares = get_squares(corners, M_inv)
    square_dict = squares_to_dict(squares)
    model = RFDETRMedium(pretrain_weights=str(project_dir / 'models' / 'rfdetr_medium_v2' / 'checkpoint_best_total.pth'), num_classes=12)
    predictions = model.predict(img)
    predict_board(square_dict, predictions)
    fen = dict_to_fen(square_dict)
    print(fen)


if __name__ == "__main__":
    main()

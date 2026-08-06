"""
A module for processing chessboard images and deriving board states.
"""

import cv2
from matplotlib import pyplot as plt
import numpy as np
import scipy.spatial as spatial
import scipy.cluster as clstr
from collections import defaultdict
import operator
import itertools

def preprocess(img):
    img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    grey = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    blur = cv2.blur(grey, (3, 3))
    return blur

def autocanny(blur):
    v = np.median(blur)
    sigma = 0.33
    l = int(max(0, (1.0 - sigma) * v))
    u = int(min(255, (1.0 + sigma) * v))
    canny = cv2.Canny(blur, l, u)
    return canny

def dilate(canny):
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(canny, kernel, iterations = 1)
    return dilated

def find_contour(dilated):
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    largest_contour = max(contours, key=cv2.contourArea)
    points = largest_contour.reshape(-1, 2)
    return points

def find_corners(points):
    #max x + y
    bottom_right, _ = max(enumerate([point[0] + point[1] for point in points]), key=operator.itemgetter(1))
    #min x + y
    top_left, _ = min(enumerate([point[0] + point[1] for point in points]), key=operator.itemgetter(1))
    #min x - y
    bottom_left, _ = min(enumerate([point[0] - point[1] for point in points]), key=operator.itemgetter(1))
    #max x - y
    top_right, _ = max(enumerate([point[0] - point[1] for point in points]), key=operator.itemgetter(1))
    corners = np.asarray([points[top_left], points[top_right], points[bottom_left], points[bottom_right]], dtype='float32')
    return corners

def warp(img, corners):
    height, width = 800, 800
    dimensions = np.float32([[0, 0],[width, 0], [0, height],[width, height]])
    M = cv2.getPerspectiveTransform(corners, dimensions)
    M_inv = cv2.invert(M)[1]
    warped = cv2.warpPerspective(img, M, (width, height))
    return warped, M_inv

def close(canny):
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(canny, cv2.MORPH_CLOSE, kernel)
    return closed

def hough_lines(closed):
    lines = cv2.HoughLines(closed, 1, np.pi/180, 180)
    return lines

def sort_lines(lines):
    lines = np.reshape(lines, (-1, 2))
    h = []
    v = []
    for rho, theta in lines:
        if theta < np.pi / 4 or theta > np.pi - np.pi/4:
            v.append([rho, theta])
        else:
            h.append([rho, theta])
    return h, v

def find_intersections(h, v):
    intersections = []
    for rho_h, theta_h in h:
        for rho_v, theta_v in v:
            a = np.array([[np.cos(theta_h), np.sin(theta_h)], [np.cos(theta_v), np.sin(theta_v)]])
            b = np.array([rho_h, rho_v])
            intersection = np.linalg.solve(a, b)
            intersections.append(intersection)
    return intersections

def cluster_intersections(intersections, max_dist=55):
    Y = spatial.distance.pdist(intersections)
    Z = clstr.hierarchy.single(Y)
    T = clstr.hierarchy.fcluster(Z, max_dist, "distance")
    clusters = defaultdict(list)
    for i in range(len(T)):
        clusters[T[i]].append(intersections[i])
    clusters = clusters.values()
    clusters = map(lambda arr: (np.mean(np.array(arr)[:, 0]), np.mean(np.array(arr)[:, 1])), clusters)
    clustered_points = []
    for point in clusters:
        clustered_points.append([point[0], point[1]])
    return clustered_points

def get_squares(corners, M_inv):
    h, w = np.max(corners, axis=0)
    x_start, y_start = np.min(corners, axis=0)
    rows = 8
    cols = 8

    # Create linearly spaced points for the grid edges
    x_points = np.linspace(x_start, w, cols + 1, dtype=int)
    y_points = np.linspace(y_start, h, rows + 1, dtype=int)
    # Create meshgrid to get the X,Y coordinates of all intersections
    xv, yv = np.meshgrid(x_points, y_points)

    # Derive the four corners of each grid square
    squares = []
    for i in range(rows):
        for j in range(cols):
            top_left = (xv[i, j], yv[i, j])
            top_right = (xv[i, j + 1], yv[i, j])
            bottom_left = (xv[i + 1, j], yv[i + 1, j])
            bottom_right = (xv[i + 1, j + 1], yv[i + 1, j]) 
            corners = [top_left, top_right, bottom_left, bottom_right]
            squares.append(corners)

    squares = np.array(squares, dtype=np.float32).reshape(-1, 1, 2)
    squares = cv2.perspectiveTransform(squares, M_inv)
    squares = squares.reshape(-1, 4, 2)
    return squares

def localise_and_extract(img):
    """Localise a chessboard in an image and extract the grid squares."""
    blur = preprocess(img)
    canny = autocanny(blur)
    dilated = dilate(canny)
    points = find_contour(dilated)
    board_corners = find_corners(points)
    warped, M_inv = warp(img, board_corners)
    closed = close(autocanny(preprocess(warped)))
    lines = hough_lines(closed)
    h, v = sort_lines(lines)
    intersections = find_intersections(h, v)
    clustered_points = cluster_intersections(intersections)
    grid_corners = find_corners(clustered_points)
    squares = get_squares(grid_corners, M_inv)
    return squares

def squares_to_dict(squares, perspective='white_left'):
    """
    Map chessboard square coordinates to a dictionary with algebraic notation keys.
    Perspective assumptions:
    - White is on the left side of the image frame.
    - Black is on the right side of the image frame.
    - Top-left: a1 | Top-right: a8 | Bottom-left: h1 | Bottom-right: h8
    Can be adjusted using the perspective parameter.

    Args:
        squares (np.ndarray): An array of shape (64, 4, 2) containing image coordinates for 64 squares.
        perspective (str): The perspective of the board. Options are 'white', 'black', 'white_left', 'white_right'.
    Returns:
        A dictionary with keys as square names in algebraic notation (e.g., 'a1', 'h8')
        and values as dictionaries containing 'predictions' (initialised to None)
        and 'corners' (square coordinates).
    """
    square_dict = {}
    files = "abcdefgh"
    ranks = "12345678"
    if perspective == 'white':
        # Top-to-bottom: 8 to 1, Left-to-right: a to h
        square_names = [f'{file}{rank}' for rank in ranks[::-1] for file in files]
    elif perspective == 'black':
        # Top-to-bottom: 1 to 8, Left-to-right: h to a
        square_names = [f'{file}{rank}' for rank in ranks for file in files[::-1]]
    elif perspective == 'white_left':
        # Top-to-bottom: a to h, Left-to-right: 1 to 8
        square_names = [f'{file}{rank}' for file in files for rank in ranks]
    elif perspective == 'white_right':
        # Top-to-bottom: h to a, Left-to-right: 8 to 1
        square_names = [f'{file}{rank}' for file in files[::-1] for rank in ranks[::-1]]
    for square, square_name in zip(squares, square_names):
        x0, y0 = np.min(square, axis=0)
        x1, y1 = np.max(square, axis=0)
        square_dict[square_name] = {'predictions': [],
                                    'corners': (float(x0), float(y0), float(x1), float(y1))}

    return square_dict

def predict_board(square_dict, detections):
    """
    Map detections to corresponding squares based on detection and square coordinates.

    Args:
        square_dict (dict): A dictionary containing square information and predictions.
        detections (list): A list of detection results.
    Returns:
        Updates the square_dict in place with predictions for each square.
    """
    label_list = ["B", "K", "N", "P", "Q", "R", "b", "k", "n", "p", "q", "r"]
    for _, square_info in square_dict.items():
        x0, y0, x1, y1 = square_info['corners']
        predictions = []
        for detection in detections:
            xyxy = detection[0]
            bottom_centre = ((xyxy[0] + xyxy[2]) / 2, xyxy[3])
            label = detection[3]
            score = detection[2]
            if x0 < bottom_centre[0] < x1 and y0 < bottom_centre[1] - 10 < y1:
                predictions.append((label_list[label], score))
        predictions.sort(key=operator.itemgetter(1), reverse=True)
        predictions = [label for label, _ in predictions]
        square_info['predictions'] = predictions

def get_fen_permutations(square_dict):
    """
    Generate FEN permutations based on square predictions.

    Args:
        square_dict (dict): A dictionary containing square information and predictions.
    Returns:
        A list of FEN strings representing all possible board configurations given the predictions.
    """

    def board_to_fen(board):
        """Build a FEN string from a nested list representation of the chessboard."""
        # store FEN ranks in list to build FEN
        fen_ranks = []
        # FEN begins at rank 8, file a and goes down to rank 1, file h i.e. a8, b8... h1
        # iterate through ranks, counting empty files and noting pieces to build rank strings
        for rank in board:
            rank_string = ''
            empty_count = 0
            for square in rank:
                if square == "":
                    empty_count += 1
                else:
                    if empty_count > 0:
                        rank_string += str(empty_count)
                        empty_count = 0
                    rank_string += square
            if empty_count > 0:
                rank_string += str(empty_count)
            fen_ranks.append(rank_string)
            
        return '/'.join(fen_ranks)
    
    board = [["" for _ in range(8)] for _ in range(8)]
    file_to_index = {'a': 0, 'b': 1, 'c': 2, 'd': 3, 'e': 4, 'f': 5, 'g': 6, 'h': 7}
    rank_to_index = {'1': 7, '2': 6, '3': 5, '4': 4, '5': 3, '6': 2, '7': 1, '8': 0}
    squares_with_alts = []

    for square in square_dict:
        file = file_to_index[square[0]]
        rank = rank_to_index[square[1]]
        predictions = square_dict[square]['predictions']
        #print(f"Square: {square}, Predictions: {predictions}")
        if len(predictions) > 1:
            squares_with_alts.append((rank, file, predictions))
        else:
            board[rank][file] = predictions[0] if predictions else ""

    fen_permutations = []

    alts = [square[2] for square in squares_with_alts]
    for combination in itertools.product(*alts):
        temp_board = [row[:] for row in board]
        for (rank, file, _), alt in zip(squares_with_alts, combination):
            temp_board[rank][file] = alt
        fen_permutations.append(board_to_fen(temp_board))

    for fen in fen_permutations:
        if fen.count('K') > 1 or fen.count('k') > 1 or fen.count('P') > 8 or fen.count('p') > 8:
            fen_permutations.remove(fen)

    return fen_permutations
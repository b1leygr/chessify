import cv2
from matplotlib import pyplot as plt
import numpy as np
import scipy.spatial as spatial
import scipy.cluster as clstr
from collections import defaultdict
import operator

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

    # Extract and print the 4 corners for each grid square
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

def squares_to_dict(squares):
    square_list = []
    for square in squares:
        x0, y0 = np.min(square, axis=0)
        x1, y1 = np.max(square, axis=0)
        square_list.append((float(x0), float(y0), float(x1), float(y1)))

    square_dict = {}
    cols = "abcdefgh"
    rows = "12345678"
    square_names = [f'{col}{row}' for col in cols for row in rows]
    for square, square_name in zip(square_list, square_names):
        square_dict[square_name] = {'piece': None, 'corners': square, 'score': None}

    return square_dict

def predict_board(square_dict, predictions):
    label_list = ["B", "K", "N", "P", "Q", "R", "b", "k", "n", "p", "q", "r"]
    for square_name, square_info in square_dict.items():
        x0, y0, x1, y1 = square_info['corners']
        for pred in predictions:
            xyxy = pred[0]
            bottom_center = ((xyxy[0] + xyxy[2]) / 2, xyxy[3])
            label = pred[3]
            score = pred[2]
            if x0 < bottom_center[0] < x1 and y0 < bottom_center[1] - 10 < y1:
                square_info['piece'] = label_list[label]
                square_info['score'] = float(score)
                # print(f"Square: {square_name}, Piece: {label_list[label]}, Score: {score}")
                break

def dict_to_fen(square_dict):
    # store FEN ranks in list to build FEN
    fen_ranks = []

    # FEN begins at rank 8, file a and goes down to rank 1, file h i.e. a8, b8... h1
    # iterate through ranks, counting empty files and noting pieces to build file strings
    for rank in '87654321':
        file_string = ''
        empty_count = 0

        for file in 'abcdefgh':
            square = f'{file}{rank}'
            piece = square_dict[square]['piece']
            if piece is None:
                empty_count += 1
            else:
                if empty_count > 0:
                    file_string += str(empty_count)
                    empty_count = 0
                file_string += piece

        if empty_count > 0:
            file_string += str(empty_count)

        fen_ranks.append(file_string)
    
    return '/'.join(fen_ranks)

from pathlib import Path

import cv2
from rfdetr import RFDETRMedium

from app.backend import chess_utils

def main():
    project_dir = Path.cwd()
    model = RFDETRMedium(
        pretrain_weights=str(
            project_dir
            / 'app'
            / 'backend'
            / 'models'
            / 'rfdetr_medium_v2'
            / 'checkpoint_best_total.pth'
        ),
        num_classes=12
    )

    while True:
        mode = input('Choose mode (1: single image, 2: batch images, 3: exit): ')

        if mode == '1':
            file = input('Choose an image file:') + '.jpg'
            file = next((project_dir/'notebooks').rglob(f'**/{file}'), None)
            if not file:
                print('File not found.')
                continue
            move_id = file.stem.split('_')[-1]
            print(f'Processing image: {file}')
            try:
                true_fens = file.parent / 'fens.csv'
                img = cv2.imread(file)
                board_grid = chess_utils.localise_and_extract(img)
                square_dict = chess_utils.squares_to_dict(board_grid)
                detections = model.predict(img)
                chess_utils.predict_board(square_dict, detections)
                fens = chess_utils.get_fen_permutations(square_dict)
                if not fens:
                    print('No valid FENs found.')
                else:
                    with open(true_fens, 'r') as true_fens_file:
                        true_fens_file.readline()
                        for line in true_fens_file:
                            if line.split(',')[0] == move_id:
                                true_fen = line.split(',')[1].strip().split(' ')[0]
                                if true_fen in fens:
                                    if len(fens) > 1:
                                        print(f'A predicted FEN matches the true FEN! {true_fen}')
                                    else:
                                        print(f'FEN matches the true FEN! {true_fen}')
                continue
            except Exception as e:
                print(f'Error: {e}. Please choose a different image file.')

        elif mode == '2':
            dir_path = project_dir / 'notebooks' / input('Enter directory path for batch images: ')
            if not dir_path.exists() or not dir_path.is_dir():
                print('Directory not found.')
                continue
            print(f'Processing images in directory: {dir_path}')
            try:
                true_fens = dir_path / 'fens.csv'
                fen_accuracy = {'game': dir_path.stem,
                                'total_images': 0,
                                'correct_predictions': 0}
                for file in dir_path.glob('*.jpg'):
                    fen_accuracy['total_images'] += 1
                    move_id = file.stem.split('_')[-1]
                    img = cv2.imread(file)
                    board_grid = chess_utils.localise_and_extract(img)
                    square_dict = chess_utils.squares_to_dict(board_grid)
                    detections = model.predict(img)
                    chess_utils.predict_board(square_dict, detections)
                    fens = chess_utils.get_fen_permutations(square_dict)
                    if not fens:
                        print('No valid FENs found.')
                    else:
                        with open(true_fens, 'r') as true_fens_file:
                            true_fens_file.readline()
                            for line in true_fens_file:
                                if line.split(',')[0] == move_id:
                                    true_fen = line.split(',')[1].strip().split(' ')[0]
                                    if true_fen in fens:
                                        if len(fens) > 1:
                                            print(f'A predicted FEN matches the true FEN! {true_fen}')
                                            fen_accuracy['correct_predictions'] += 1/len(fens)
                                        else:
                                            print(f'FEN matches the true FEN! {true_fen}')
                                            fen_accuracy['correct_predictions'] += 1
                print(f'Game: {fen_accuracy["game"]}, '
                      f'Total images: {fen_accuracy["total_images"]}, ' 
                      f'Correct predictions: {fen_accuracy["correct_predictions"]}, ' 
                      f'Accuracy: {fen_accuracy["correct_predictions"]/fen_accuracy["total_images"]:.2%}')
                continue
            except Exception as e:
                print(f'Error: {e}. Please choose a different directory path.')
        
        elif mode == '3':
            print('Exiting...')
            break


if __name__ == "__main__":
    main()

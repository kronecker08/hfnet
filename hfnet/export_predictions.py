import numpy as np
import argparse
import yaml
import logging
from pathlib import Path
from tqdm import tqdm
from pprint import pformat

logging.basicConfig(format='[%(asctime)s %(levelname)s] %(message)s',
                    datefmt='%m/%d/%Y %H:%M:%S',
                    level=logging.INFO)
from hfnet.models import get_model  # noqa: E402
from hfnet.datasets import get_dataset  # noqa: E402
from hfnet.utils import tools  # noqa: E402
from hfnet.settings import EXPER_PATH, DATA_PATH  # noqa: E402


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=str)
    parser.add_argument('export_name', type=str)
    parser.add_argument('--keys', type=str, default='*')
    parser.add_argument('--exper_name', type=str)
    parser.add_argument('--as_dataset', action='store_true')
    args = parser.parse_args()

    export_name = args.export_name
    exper_name = args.exper_name
    with open(args.config, 'r') as f:
        config = yaml.load(f)
    keys = '*' if args.keys == '*' else args.keys.split(',')

    if args.as_dataset:
        base_dir = Path(DATA_PATH, export_name)
    else:
        base_dir = Path(EXPER_PATH, 'exports')
        base_dir = Path(base_dir, ((exper_name+'/') if exper_name else '') + export_name)
    base_dir.mkdir(parents=True, exist_ok=True)

    if exper_name:
        # Update only the model config (not the dataset)
        with open(Path(EXPER_PATH, exper_name, 'config.yaml'), 'r') as f:
            config['model'] = tools.dict_update(
                yaml.load(f)['model'], config.get('model', {}))
        checkpoint_path = Path(EXPER_PATH, exper_name)
        if config.get('weights', None):
            checkpoint_path = Path(checkpoint_path, config['weights'])
    else:
        if config.get('weights', None):
            checkpoint_path = Path(DATA_PATH, 'weights', config['weights'])
        else:
            checkpoint_path = None
            logging.info('No weights provided.')
    logging.info(f'Starting export with configuration:\n{pformat(config)}')

    with get_model(config['model']['name'])(
            data_shape={'image': [None, None, None, config['model']['image_channels']]},
            **config['model']) as net:
        if checkpoint_path is not None:
            net.load(str(checkpoint_path))
        dataset = get_dataset(config['data']['name'])(**config['data'])
        test_set = dataset.get_test_set()

        for data in tqdm(test_set):
            predictions = net.predict(data, keys=keys)
            predictions['input_shape'] = data['image'].shape
            name = data['name'].decode('utf-8')
            Path(base_dir, Path(name).parent).mkdir(parents=True, exist_ok=True)
            np.savez(Path(base_dir, '{}.npz'.format(name)), **predictions)
#python3 hfnet/export_predictions.py hfnet/configs/superpoint_export_aachen_db.yaml superpoint/aachen --keys keypoints,scores,local_descriptor_map 

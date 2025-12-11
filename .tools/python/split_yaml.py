from pathlib import Path
import argparse
import yaml

def main(input_file='index.yaml', output_dir='.'):
    with open(input_file, 'r') as f:
        data = yaml.safe_load(f)

    for key, value in data.items():
        output_file = Path(output_dir) / f"{key}.yaml"
        with open(output_file, 'w') as f:
            yaml.dump(value, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Split a YAML index file into individual files.")
    
    parser.add_argument('--input_file', type=str, default='index.yaml', help='Input index file name')
    parser.add_argument('--output_dir', type=str, default='.', help='Directory to save the split files')

    args = parser.parse_args()

    # Assert that the paths exist
    if not Path(args.input_file).exists():
        raise FileNotFoundError(f"Input file '{args.input_file}' does not exist.")
    if not Path(args.output_dir).exists():
        print(f"Output directory '{args.output_dir}' does not exist. It will be created.")
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    main(input_file=args.input_file, output_dir=args.output_dir)
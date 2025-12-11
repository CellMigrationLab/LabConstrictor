from pathlib import Path
import argparse
import yaml

def main(input_file='index.yaml', output_dir='.', main_key='antibodies', grouping_key='target_gene'):
    with open(input_file, 'r') as f:
        data = yaml.safe_load(f)

    antibodies = {}

    for case in data[main_key]:
        target_gene = case[grouping_key]
        if target_gene not in antibodies:
            antibodies[target_gene] = []
        # Remove the gene key from the case dictionary
        case_copy = case.copy()
        case_copy.pop(grouping_key, None)

        antibodies[target_gene].append(case_copy)

    print(f"Found {len(antibodies)} unique target genes.")
    for gene, cases in antibodies.items():
        print(f"Gene: {gene}, Cases: {len(cases)}")

    for key, value in antibodies.items():
        output_file = Path(output_dir) / f"{key}.yaml"
        with open(output_file, 'w') as f:
            yaml.dump(value, f)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Split a YAML index file into individual files.")
    
    parser.add_argument('--input_file', type=str, default='index.yaml', help='Input index file name')
    parser.add_argument('--output_dir', type=str, default='.', help='Directory to save the split files')
    parser.add_argument('--main_key', type=str, default='antibodies', help='Main key to process')
    parser.add_argument('--grouping_key', type=str, default='target_gene', help='Key to group by')

    args = parser.parse_args()

    # Assert that the paths exist
    if not Path(args.input_file).exists():
        raise FileNotFoundError(f"Input file '{args.input_file}' does not exist.")
    if not Path(args.output_dir).exists():
        print(f"Output directory '{args.output_dir}' does not exist. It will be created.")
        Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    main(input_file=args.input_file, output_dir=args.output_dir, 
         main_key=args.main_key, grouping_key=args.grouping_key)
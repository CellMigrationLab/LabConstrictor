from pathlib import Path
import argparse
import yaml

def main(lab_database_path):

    # Go through all directories in the specified path
    for folder_path in Path(lab_database_path).rglob('*'):
        if folder_path.is_dir() and not folder_path.name.startswith('.'):
            output_file = lab_database_path / Path(f'{folder_path.name}.yaml')

            # Dictionary to hold the output data
            output_dict = {}

            # Go through all files in the specified directory
            for file_path in Path(folder_path).rglob('*'):
                if file_path.is_file() and not file_path.name.startswith('.'):
                    if file_path.suffix in ['.yaml', '.yml']:
                        output_dict[str(file_path.stem)] = {
                            'path': f"{folder_path.name}/{file_path.name}"
                        }

            # Write the output dictionary to the specified YAML file
            with open(output_file, 'w') as f:
                yaml.dump(output_dict, f, default_flow_style=False)

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser(description="Generate an index file for the project.")

    parser.add_argument('--lab_database_path', type=str, default='index.yaml', help='Directory where the configurations are stored')

    args = parser.parse_args()

    main(lab_database_path=args.lab_database_path)
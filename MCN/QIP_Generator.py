import os
import re
import sys

if len(sys.argv) != 2:
    raise ValueError('Usage: QIP_enerator.py Poly|DD')

mode = sys.argv[1]

if mode not in ('Poly', 'DD'):
    raise ValueError('Input parameter must be either "Poly" or "DD"')

input_directory = 'Instances/raw'
output_directory = 'Instances/QIP_'+mode

for root, dirs, files in os.walk(input_directory):
    for Filename in files:
        #print(Filename)

        input_path = os.path.join(root, Filename)

        # Determine the relative subdirectory inside "raw"
        relative_dir = os.path.relpath(root, input_directory)
        parts = relative_dir.split(os.sep)
        # Create the corresponding directory inside the output directory
        if relative_dir == '.':
            output_folder = output_directory
        elif len(parts) >= 2 and parts[1].startswith('rndgraph'):
            output_folder = os.path.join(output_directory, 'rndgraph')

        elif len(parts) >= 2 and parts[1].startswith('tree'):
            output_folder = os.path.join(output_directory, 'tree')
        else:
             main_type = parts[0]
             output_folder = os.path.join(output_directory, main_type)

        os.makedirs(output_folder, exist_ok=True)

        with open(input_path) as f:
            lines = f.readlines()

        match = re.search(r'(?<!\d)(\d+)-(\d+)-(\d+)(?!\d)', Filename)


        if match is None:
            print(f"Skipping {Filename}: no Omega-Theta-Lambda parameters found")
            continue

        Omega, Theta, Lambda = map(int, match.groups())

        #print(f"{Filename}: Omega={Omega}, Theta={Theta}, Lambda={Lambda}")

        Arcs = []
        content = []
        nodes = []

        for line in lines:
            if line[0] == 'A' and line[2] == '=':
                content = line[6:-3].split('), (')

            if line[0] == 'V' and line[2] == '=':
                nodes = line[5:-2].split(', ')

        for arc in content:
            Arcs.append(arc.split(', '))

        # Access arc i by Arcs[i][0] and Arcs[i][1]

        output_path = os.path.join(output_folder, Filename + '.qlp')

        with open(output_path, 'w') as f:
            f.write('MAXIMIZE\n')

            for v in nodes:
                f.write('+ alpha_' + str(v) + ' ')

            f.write('\nSUBJECT TO\n')

            for v in nodes:
                f.write('+ z_' + str(v) + ' ')
            f.write('<= ' + str(Omega) + '\n')

            for v in nodes:
                f.write('+ x_' + str(v) + ' ')
            f.write('<= ' + str(Lambda) + '\n')

            for v in nodes:
                if mode == 'Poly':  
                    f.write(
                        '+ alpha_' + str(v)
                        + ' - z_' + str(v)
                        + ' + y_' + str(v)
                        + ' <= 1\n'
                    )
                else:
                    f.write(
                        '+ alpha_' + str(v)
                        + ' + y_' + str(v)
                        + ' <= 1\n'
                    )

            for i in range(len(Arcs)):
                f.write(
                    '+ alpha_' + str(Arcs[i][1])
                    + ' - alpha_' + str(Arcs[i][0])
                    + ' - x_' + str(Arcs[i][1])
                    + ' - z_' + str(Arcs[i][1])
                    + ' <= 0\n'
                )

            f.write('UNCERTAINTY SUBJECT TO\n')
            for v in nodes:
                f.write('+ y_' + str(v) + ' ')
            f.write('<= ' + str(Theta) + '\n')
            if mode == 'DD':
                for v in nodes:
                    f.write('+ y_'+str(v)+' + z_'+str(v)+' <= 1\n')
            f.write('BOUNDS\n')

            for v in nodes:
                f.write('0 <= x_' + str(v) + ' <= 1\n')
                f.write('0 <= y_' + str(v) + ' <= 1\n')
                f.write('0 <= z_' + str(v) + ' <= 1\n')
                f.write('0 <= alpha_' + str(v) + ' <= 1\n')

            f.write('BINARIES\n')

            for v in nodes:
                f.write('x_' + str(v) + '\n')
                f.write('y_' + str(v) + '\n')
                f.write('z_' + str(v) + '\n')

            f.write('EXISTS\n')

            for v in nodes:
                f.write('x_' + str(v) + '\n')
                f.write('z_' + str(v) + '\n')
                f.write('alpha_' + str(v) + '\n')

            f.write('ALL\n')

            for v in nodes:
                f.write('y_' + str(v) + '\n')

            f.write('ORDER\n')

            for v in nodes:
                f.write('z_' + str(v) + '\n')

            for v in nodes:
                f.write('y_' + str(v) + '\n')

            for v in nodes:
                f.write('x_' + str(v) + '\n')

            for v in nodes:
                f.write('alpha_' + str(v) + '\n')

            f.write('END')

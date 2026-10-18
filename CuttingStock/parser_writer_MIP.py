import sys
from xml.dom import minidom
from pathlib import Path

# abort if no qlp was given as argument
if len(sys.argv) < 4:
    print('not enough arguments\nshutting down ...')
    sys.exit(1)

# save name from qlp
folder =  sys.argv[1]
name = sys.argv[2].replace('.qlp', '')
out = sys.argv[3]
log = sys.argv[3].replace('_check.qlp', '')
sol = folder +  "/CPLEX_MIP/" + name + '.sol'

my_file = Path(sol)
if not  my_file.is_file():
    sys.exit(1)

# use xml parser to get variables with attributes
importedSol = minidom.parse(sol)
solItems = importedSol.getElementsByTagName('variable')

doc = open('instances/data/' + name + '.raw', 'r')
docm = doc.read().split('\n')

# string variable
initialItem = ''
NumStages = ''

for i in range(0, len(docm)):
    if 'Initial Item=' in docm[i]:
        initialItem = docm[i].split('=')
        initialItem = initialItem[1]
        #print('Initial Item is ' +initialItem)
    elif 'T=' in docm[i]:
        NumStages = docm[i].split('=')
        NumStages = NumStages[1]
        #print('NumStages is ' +NumStages)



doc.close()
# declare lists for items and variable to store T
aItems = []
uItems = []
b2ItemSize = 0

# write additional constraints to fullstring
for i in range(0, len(solItems)):
    # check if a is in variable name
    if 'a' in solItems[i].attributes['name'].value:
        aItems.append(solItems[i])
        #print('Append: ' +solItems[i].attributes['name'].value)

# open original qlp and open modified qlp
doc = open(folder + '/instances/QLP/' + name + '.qlp', 'r')
moddoc = open(out, 'w')

# read original qlp to ram (faster than line-based)
rdoc = doc.read()
# split qlp at constraint block
rdoc = rdoc.split('SUBJECT TO\n')

# write first part of original qlp to variable fullstring
fullString = rdoc[0] + 'SUBJECT TO\n'

# write additional constraints to fullstring
for i in range(0, len(aItems)):
    # write to constraint to fullstring

    #split variable name in underscore seperated list vname
    vname = aItems[i].attributes['name'].value
    #print(vname)

    vname = vname.split('_')


    #construct variables a_t_b_i and write to fullstring

    #check if i = 0
    if vname[2] == initialItem:
        fullString += '+' + vname[0] + '_0_' + vname[1] + '_0 '
        for j in range(1, int(NumStages) ):
            fullString += '+' + vname[0] + '_' + str(j) + '_' + vname[1] + '_' + vname[2] + ' '
    else:
        for j in range(1, int(NumStages) ):
            fullString += '+' + vname[0] + '_' + str(j) + '_' + vname[1] + '_' + vname[2] + ' '

    #write right side of constraint
    fullString += '= ' + str(int(round(float(aItems[i].attributes['value'].value)))) + '\n'

# write second part of original qlp to fullstring
fullString += rdoc[1] + 'SUBJECT TO\n'
fullString += rdoc[2]
# write fullstring to modified qlp file
moddoc.write(fullString)

# close opened documents
doc.close()
moddoc.close()

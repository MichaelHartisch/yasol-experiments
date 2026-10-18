import sys
from xml.dom import minidom
from pathlib import Path


# abort if no qlp was given as argument
if len(sys.argv) < 3:
    print('not enough arguments\nshutting down ...')
    sys.exit(1)

# save name from qlp
outname = sys.argv[2]
solname = sys.argv[1]
instname= sys.argv[3]
# use xml parser to get variables with attributes
importedSol = minidom.parse(solname)
solItems = importedSol.getElementsByTagName('variable')

# declare lists for items and variable to store T
aItems = []
uItems = []
Stages = 0

# write additional constraints to fullstring
for i in range(0, len(solItems)):
    # check if a is in variable name
    if 'a' in solItems[i].attributes['name'].value:
        aItems.append(solItems[i])
    # check if variable is from block 2
    # if true, get T
    elif '2' == solItems[i].attributes['block'].value:
        # read value from name and split at underscore
        zSplit = solItems[i].attributes['name'].value.split('_')
        # get T from the middle of the underscore seperated list
        Stages = max(int(zSplit[1]),Stages)
    elif 'u_0_' in solItems[i].attributes['name'].value and solItems[i].attributes['value'].value == '1':
        #print(solItems[i].attributes['name'].value)
        uItems.append(solItems[i].attributes['name'].value)

# check if one u_0* variable has value = 1
# if not, print instance name and amount of u_0* variables with value 1 to terminal
if len(uItems) != 1:
    print(solname + ' has more than ' + str(len(uItems)) + ' items with name u_0* that have value 1')
    #for i in uItems:
        #print(i)
    sys.exit(1)

# set b2itemsize to i in u_0* variable
uItemSize = uItems[0].split('_')
#uItemSize = uItemSize[-1]
startItem = uItemSize[-1]

# open original qlp and open modified qlp
doc = open(instname , 'r')
moddoc = open(outname, 'w')

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
    vname = vname.split('_')

    #construct variables a_t_b_i and write to fullstring

    #check if i = 0
    if vname[2] == startItem:
        fullString += '+ ' + vname[0] + '_0_' + vname[1] + '_0 '
        for j in range(1, Stages + 1):
            fullString += '+ ' + vname[0] + '_' + str(j) + '_' + vname[1] + '_' + vname[2] + ' '
    else:
        for j in range(1, Stages + 1):
            fullString += '+ ' + vname[0] + '_' + str(j) + '_' + vname[1] + '_' + vname[2] + ' '

    #write right side of constraint
    fullString += '= ' + str(round(float(aItems[i].attributes['value'].value))) + '\n'

# write second part of original qlp to fullstring
fullString += rdoc[1] + 'SUBJECT TO\n'
fullString += rdoc[2]
# write fullstring to modified qlp file
moddoc.write(fullString)

# close opened documents
doc.close()
moddoc.close()

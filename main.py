# import hou
import sys
from saveshader import write_data
from readshader import read_data


def main(inchoice=None, mynodes=None):
    if inchoice == 0:
        print '---- Saving out Shader data for Nodes -', ','.join(mynodes), ' -----'
        write_data(mynodes)
    elif inchoice == 1:
        print '---- Checking for Shader data to read into Scene. ----'
        read_data()

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))

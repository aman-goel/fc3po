#!/usr/bin/python -i
## Change above to point to your python.  The -i option leaves you in
## interactive mode after the script has completed. Use ctrl-d to exit
## python.

## Import the repycudd module

class parser():
    def __init__(self):
        self.nothing = []
        self.data_location = "data/client_server/"

    def read_pla(self, file_id):
        # this function extracts the variables and cubes from a .pla file
        # It is used within the "read_all" function below on each .pla file defined in the init file
        mylines = []
        raw_input = []
        cubes = []
        lines = file_id.readlines()
        variable_name_list = []
        for line in lines:
            if ".ilb" in line: # find the variable names
                raw_input.append(line)
                raw_input_str = str(raw_input)
                raw_input_str = raw_input_str[:-4] #remove the \n a the end

                while(raw_input_str): #finding the variable names divided by spaces
                    var_name = re.search(' (.+?) ', raw_input_str)
                    rm_index = raw_input_str.find(' ')
                    raw_input_str = raw_input_str[rm_index+2:]
                    if var_name:
                        found = var_name.group(1)
                        variable_name_list.append(found)

            elif ".phase 0" in line:
                index = lines.index('.phase 0\n')
                cubes = lines[index+1:-1]
                for cube in cubes: # Strip off the unneeded 1 and space at the end
                    cubes[cubes.index(cube)] = str(cube[:-2])

        for var in variable_name_list: # Really hacky, because the file names have a space before commas
                                       # but in the files theres no spaces in the names. I choose to add a space here.
            index = variable_name_list.index(var)
            variable_name_list[variable_name_list.index(var)] = var.replace(',', ', ')
        return cubes, variable_name_list

    def open_all_pla(self, init_file_name):
        # This function reads the variables and cubes from each .pla file
        # in the init.pla file. Call it by giving the name/dir of your init file
        # and it returns 2D lists of cubes and variable names.
        # The first dimension is within the files, and the second is to switch between files.

        # It may be useful to add functionality to include where the data came from (which .pla file)
        cubes = []
        variable_names = []

        file_id = open(str(init_file_name),"r")
        [cubes_new, variable_name_list] = self.read_pla(file_id) # grab the names from the init file
        variable_names.append(variable_name_list)
        cubes.append(cubes_new) # Get the init cube and append it to our cube list

        unique_file_names_set = set() # Set addition to only get unique names because
                     # files have no '__' varibles and order doesn't matter

        for var in variable_name_list: # For each variable save only uniques

            if re.search('__', var):
                if str(var[2:]) not in unique_file_names_set: # Collect only unique names
                    unique_file_names_set.add(str(var[2:]))
                continue
            if str(var) not in unique_file_names_set:
                unique_file_names_set.add(str(var))

        unique_file_names_list = list(unique_file_names_set) # Change the type so we can iterate
        for file_name in unique_file_names_list:
            file_id = open(self.data_location+file_name+".pla","r")
            [cubes_new, variable_name_list] = self.read_pla(file_id) # grab the names from the init file
            cubes.append(cubes_new)
            variable_names.append(variable_name_list)
        return cubes, variable_names



##################################     Parser above      ###############################################

class forward_reachability():
    def __init__(self):
        self.mgr = repycudd.DdManager()
        self.name2bdd = {}
        # Initialize the present and next state dd arrays
        self.present_state_DDArray = repycudd.DdArray(self.mgr, 2)
        self.next_state_DDArray = repycudd.DdArray(self.mgr, 2)

    def print_dd (self, dd, n, pr ):
        #self.print_dd(source,2,2)
        print("DdManager nodes: ", self.mgr.ReadNodeCount());            # /*Reports the number of live nodes in BDDs and ADDs*/
        print("DdManager vars: ", self.mgr.ReadSize() );                  # /*Returns the number of BDD variables in existence*/
        print("DdManager reorderings: ", self.mgr.ReadReorderings() );     #/*Returns the number of times reordering has occurred*/
        print("DdManager memory: ", self.mgr.ReadMemoryInUse() );         #/*Returns the memory in use by the manager measured in bytes*/
        self.mgr.PrintDebug(dd, n, pr);                                        #/*Prints to the standard output a DD and its statistics: number of nodes, number of leaves, number of minterms*/


    def initialize_variables(self, names):
        # initalize a new variable for each variable name
        for name in names:
            if name not in self.name2bdd:
                temp_new_var = self.mgr.NewVar()
                self.name2bdd[name] = temp_new_var

    def cube2bdd(self, cube, names):
        temp_new_cube = self.mgr.One() # Initalize the cube to 1 so we can 'and' it.
        for idx, name in enumerate(names):
            literal = cube[idx] # Get one literal from the cube
            if (literal == "1"): # And it into the cube
                temp_new_cube = self.mgr.And(temp_new_cube, self.name2bdd[name])
            elif (literal == "0"): # Not then And it
                temp_new_cube = self.mgr.And(temp_new_cube, self.mgr.Not(self.name2bdd[name]))
            #elif literal == "-": do nothing
        return temp_new_cube

    def construct_bdd(self, cubes, names):## need next states?
        # Take a list of cubes and list of names and build the BDD (one file)
        bool_function = self.mgr.Zero() # Initialize to zero because we're "Oring"
        for cube in cubes:
            bool_function = self.mgr.Or(bool_function, self.cube2bdd(cube, names))
        return bool_function

    def parse(self):
        p = parser()
        [list_of_cubes, list_of_names] = p.open_all_pla(p.data_location+"init.pla")
        return list_of_cubes, list_of_names


    def execute_bdd_build(self):
        #list_of_cubes/names are lists of lists, the first row is from the init file.
        [list_of_cubes, list_of_names] = self.parse()

        initcubes = list_of_cubes[0]
        prenames = list_of_names[0]
        self.initialize_variables(prenames) # Initialize the variables in the init.pla file
        next_state_names = []

        for name in prenames:
            next_state_name = name.replace('_', '') # Stripping the double underscore "__" gives us next state variables
            next_state_names.append(next_state_name)

        self.initialize_variables(next_state_names) # Initialize the next state variable_names
        init_bool_function = self.construct_bdd(initcubes, prenames)
        transition_relation = init_bool_function ############# check this?

        for index, name in enumerate(list_of_names[1:]):
            next_bool_function = self.construct_bdd(list_of_cubes[index], list_of_names[index])
            transition_relation = self.mgr.Or(transition_relation, next_bool_function)
        return init_bool_function, transition_relation

    def create_abstraction_cube(self):
        cubeP_names = ["temp1", "temp2", "temp3", "temp4" ]
        cubeP_cubes = ['1111'] # Not sure what we need for cubeP, but this doesn't break the code.
        cubeP = self.construct_bdd(cubeP_names, cubeP_cubes)
        return cubeP

    def states_to_array(self): # the next and current states need to be placed in a repy DDArray
        for key in self.name2bdd.keys():
            if "_" in key:
                #present_state_keys.append(self.name2bdd[key]) # not currently used
                self.present_state_DDArray.Push(self.name2bdd[key])
            else:
                #next_state_keys.append(self.name2bdd[key]) # not currently used
                self.next_state_DDArray.Push(self.name2bdd[key])
        return 0

    def step_forward(self, source, transition_relation, cubeP): # Steps forward once
        temp_next = self.mgr.AndAbstract(source, transition_relation, cubeP) # image of new nodes
        next_state_image = self.mgr.SwapVariables(temp_next, self.present_state_DDArray, self.next_state_DDArray, 2) # switch the next and present state variables
        return next_state_image

    def find_reachability(self):#, transition_relation):
        [source, transition_relation] = self.execute_bdd_build() # builds the bdd from the init.pla files
        cubeP = self.create_abstraction_cube() # makes cubeP but I'm not sure what this is for right now.
        total_reachable = source # Inital state

        # Build DD arrays for present and next states
        self.states_to_array() # updates the global variables present_state_DDArray and next_state_DDArray

        while(True):# Until we have no more new states
            new_R = total_reachable

            image = self.step_forward(source, transition_relation, cubeP)

            new_R = self.mgr.Or(image, new_R) # add this onto the reachable set

            new_source = self.mgr.And(new_R, self.mgr.Not(total_reachable)) # only returns new reached states

            if (new_source == self.mgr.Zero()):
                break #end if no new states have been reached
            total_reachable = new_R # update the reached set
            source = new_source # change the source to the new reached states

        print("Reached States: ")
        self.print_dd(total_reachable, 2, 2)
        return 0

def main(args):
    fr = forward_reachability()
    fr.find_reachability()

    return 0

if __name__ == '__main__':
    import sys
    import repycudd
    #import numpy as np
    import re
    sys.exit(main(sys.argv))

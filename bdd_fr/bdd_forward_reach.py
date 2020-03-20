#!/usr/bin/python -i
## Change above to point to your python.  The -i option leaves you in
## interactive mode after the script has completed. Use ctrl-d to exit
## python.

## Import the repycudd module
import repycudd
import numpy as np

import re

class parser():
    def __init__(self):
        self.nothing = []


    # def __init__(self):
    # return

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
        #print(unique_file_names_set)

        unique_file_names_list = list(unique_file_names_set) # Change the type so we can iterate
        for file_name in unique_file_names_list:
            file_id = open("data/"+file_name+".pla","r")
            [cubes_new, variable_name_list] = self.read_pla(file_id) # grab the names from the init file
            cubes.append(cubes_new)
            variable_names.append(variable_name_list)
        #print(variable_names)

        return cubes, variable_names



##################################     Parser above      ###############################################

class forward_reachability():
    def __init__(self):
        self.mgr = repycudd.DdManager()
        self.name2bdd = {}

    def print_dd (self, dd, n, pr ):
        #self.print_dd(source,2,2)
        print("DdManager nodes: ", self.mgr.ReadNodeCount());            # /*Reports the number of live nodes in BDDs and ADDs*/
        print("DdManager vars: ", self.mgr.ReadSize() );                  # /*Returns the number of BDD variables in existence*/
        print("DdManager reorderings: ", self.mgr.ReadReorderings() );     #/*Returns the number of times reordering has occurred*/
        print("DdManager memory: ", self.mgr.ReadMemoryInUse() );         #/*Returns the memory in use by the manager measured in bytes*/
        #self.mgr.PrintDebug( dd, n, pr);                                        #/*Prints to the standard output a DD and its statistics: number of nodes, number of leaves, number of minterms*/


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

    def parse(self, init_file_name):
        p = parser()
        [list_of_cubes, list_of_names] = p.open_all_pla(init_file_name)
        return list_of_cubes, list_of_names


    def execute(self):
        init_file_name = "data/init.pla"
        #list_of_cubes/names are lists of lists, the first row is from the init file.
        [list_of_cubes, list_of_names] = self.parse("data/init.pla")

        initcubes = list_of_cubes[0]
        prenames = list_of_names[0]
        self.initialize_variables(prenames) # Initialize the variables in the init.pla file
        next_state_names = []
        for name in prenames:
            next_state_name = name.replace('_', '') # Stripping the double underscore "__" gives us next state variables
            next_state_names.append(next_state_name)

        self.initialize_variables(next_state_names) # Initialize the next state variable_names

        ## better names for binit? what is this exactly?
        init_bool_function = self.construct_bdd(initcubes, prenames)
        transition_relation = init_bool_function ############# check this?
        for index, name in enumerate(list_of_names[1:]):
            #next_state_cubes, next_state_names = self.parse(n+".pla")
            ## better names for bn? what is this exactly?
            next_bool_function = self.construct_bdd(list_of_cubes[index], list_of_names[index])
            transition_relation = self.mgr.Or(transition_relation, next_bool_function)
        #self.mgr.PrintMinterm(total_function)


        return init_bool_function, transition_relation

        #edge set = transition relation?
        # curr_I?

    def find_reachability(self):#, transition_relation):
        #print("------------------------------------")
        [source, transition_relation] = self.execute()
        # repycudd.set_iter_meth(1)
        #
        # for node in repycudd.ForeachNprint(self.mgr.VectorSupportSize(source,source))odeIterator(self.mgr, source):
        #     self.mgr.PrintMinterm(node)
        # return
        cubeP_names = ["temp1", "temp2", "temp3", "temp4" ]
        cubeP_cubes = ['1111']
        cubeP = self.construct_bdd(cubeP_names, cubeP_cubes)
        #self.mgr.PrintMinterm(cubeP)
        total_reachable = source #inital state
        while(True):# Until we have no more new states
            #print('hello')
            new_R = total_reachable
            #[break_condition, reachable_one_step] = self.step_forward(source, transition_relation, cubeP)

            temp_next = self.mgr.AndAbstract(source, transition_relation, cubeP) ## image of new nodes

            ## I can't figure out how to use this and I think it's because I still don't understand it.
            #temp_curr = self.mgr.SwapVariables(temp_next, temp_next, cubeP,4)
            reachable_one_step = self.mgr.AndAbstract(source, transition_relation, cubeP) ## image of new nodes

            new_R = self.mgr.Or(reachable_one_step, new_R)

            not_R = self.mgr.Not(total_reachable)

            new_source = self.mgr.And(new_R, not_R) # returns the new present states

            # the condition to break needs to be fixed,
            num_of_vars = 4 # what is a way to check if the new_source is empty?
            if (self.mgr.CountMinterm(new_source,num_of_vars) == 0):
                break
            total_reachable = new_R
            source = new_source
            print("Reached States: ")
            self.print_dd(source,2,2)
        self.print_dd(new_R,2,2)


        #ps_cp?
        #ns_cp?
        #Cubep == return from build bdd
        #

        #
        # CubeP = construct_bdd(cubes, names)
        # while(True):
        #     step_forward(total_function)


    #def step_forward(self, source, transition, cubeP):
        #temp_next = self.mgr.AndAbstract(source, transition_relation, cubeP) ## image of new nodes
        #temp_curr = self.mgr.SwapVariables(temp_next, source, source, 4)






        def create_abstraction_cube(self):
            ps_cP = []
            ps_cP.append("111")
            ns_cP.append("---")

            #Cudd_DumpDot graphs a bdd





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


################## Start BDD builder ##############################
#
#
# def construct_bdd(mgr, f, vars, cubes, N, E):
#
#     #define a function for zero case
#     def bool_zero():
#         tmp_neg = mgr.Not(vars[j])
#         mgr.Ref(tmp_neg)
#         tmp = mgr.And(tmp_neg,cube[i])
#         mgr.Ref(tmp)
#         cube[i] = tmp
#         #break
#
#     #define a function for 'one' case
#     def bool_one():
#         tmp = mgr.And(mgr,next_state[i])
#         mgr.Ref(tmp)
#         cube[i] = tmp
#         #break
#         #switch function
#
#     def Bool_value(argument):
#         switch_case = { # dictionary
#                     0: bool_zero,
#                         #break,
#                     1: bool_one
#         }
#         func = switch_case.get(arg, lambda: 'switcher failed')
#         func()
#
#
#     cube = repycudd.DdArray(mgr, E)
#     repycudd.set_iter_meth(0)
#     for cube in repycudd.ForeachCubeIterator(m, rel):
#         cube[i] = mgr.ReadOne()
#
#         for j in range(N):
#                 Bool_value(cubes[i][N - (1 + j)])
#
#     f = mgr.ReadLogicZero()
#
#     for i in range(E): # or each cube together
#         tmp = mgr.Or(cube[i],f)
#         f = tmp
#
#     return f
#
# def main():
#     in_vars_num = 3
#     out_var = 1
#     mgr = repycudd.DdManager()
#     inames = { "x0", "x1", "x2" }    #Names for input variables */
#     onames = { "f" }
#     x = repycudd.DdArray(mgr, in_vars_num)
#     for i in range(in_vars_num):
#         x.Push(mgr.IthVar(i))
# 		#// x0,x2,x3
# 	       #x = np.append(x, mgr.NewVar())
#     cubes_f = { "101" }
#     f = None
#     f = construct_bdd(mgr, f, x, cubes_f, 3, 1)
#
#     add = mgr.ToAdd(gbm, f) #                   			/*Convert BDD to ADD for display purpose*/
#     f = add
#
# main()

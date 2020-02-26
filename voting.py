
from __future__ import print_function
import copy

numA = 3
numV = 2
numB = 2
numQ = numA

NONE = 0

outFile = "out"
outF = None
def fprint(s):
    global outF
    outF.write(s + "\n")


class State():
    def __init__(self, state=None):
        if state == None:
            self.reset()
        else:
            self.copy(state)
    
    def copy(self, state):
        self.maxBal = copy.deepcopy(state.maxBal)
        self.votes = copy.deepcopy(state.votes)
        self.member = copy.deepcopy(state.member)

    def __key(self):
        return (str(self.maxBal), str(self.votes))

    def __hash__(self):
        return hash(self.__key())

    def __eq__(self, other):
        return (self.__class__ == other.__class__ and
                self.maxBal == other.maxBal and
                self.votes == other.votes)

    def reset(self):
        self.maxBal = [-1 for i in range(numA)]
        self.votes = [[[False for k in range(numV)] for j in range(numB)] for i in range(numA)]
        self.member = [[False for j in range(numQ)] for i in range(numA)]
        self.member[0][0] = True
        self.member[1][0] = True
        self.member[0][1] = True
        self.member[2][1] = True
        self.member[1][2] = True
        self.member[2][2] = True
    
    def str(self, prefix="\t"):
        res = ""
        res += prefix + "maxBal: "
        for i in range(numA):
            if (self.maxBal[i] != -1):
                res += "A" + str(i) + ": " + str(self.maxBal[i]) + "  "
        res += "\n"
        res += prefix + "votes: "
        for i in range(numA):
            for j in range(numB):
                for k in range(numV):
                    if self.votes[i][j][k]:
                        res += "A" + str(i) + ": (B" + str(j) + ", V" + str(k) + ")  "
        res += "\n"
        return res
    
    def str_header_espresso(self):
        res = ""
        for a in range(numA):
            for b in range(-1, numB):
                res += "maxBal(A%d)=%d " % (a, b)
        res += " "
        for a in range(numA):
            for b in range(numB):
                for v in range(numV):
                    res += "votes(A%d,%d,V%d) " % (a, b, v)
            res += " "
        return res
        
    def str_espresso(self):
        res = ""
        for a in range(numA):
            for b in range(-1, numB):
                if (self.maxBal[a] == b):
                    res += "1"
                else:
                    res += "0"
        res += " "
        for a in range(numA):
            for b in range(numB):
                for v in range(numV):
                    if self.votes[a][b][v]:
                        res += "1"
                    else:
                        res += "0"
            res += " "
        return res
        

class System():
    def __init__(self):
        self.R = set()
        self.forwardReach()
            
    def votedFor(self, state, a, b, v):
        return state.votes[a][b][v]
    
    def didNotVoteAt(self, state, a, b):
        return all(not self.votedFor(state, a, b, v) for v in range(numV))
        
    def showsSafeAt(self, state, Q, b, v):
        for a in range(numA):
            if state.member[a][Q]:
                if not (state.maxBal[a] >= b):
                    return False
        condOr = False
        for c in range(-1, b):
            if c != -1:
                if not any(state.member[a][Q] and state.votes[a][c][v] for a in range(numA)):
                    continue
            for d in range(c+1, b):
                if any(state.member[a][Q] and not self.didNotVoteAt(state, a, d) for a in range(numA)):
                    continue
            condOr = True
        if not condOr:
            return False
        return True
    
    def increaseMaxBal(self, state, a, b):
        if not (b > state.maxBal[a]):
            return False, state
        
        dest = State(state)
        dest.maxBal[a] = b
        return True, dest
    
    def voteFor(self, state, a, b, v):
        if not (state.maxBal[a] <= b):
            return False, state
        for vote in state.votes[a][b]:
            if vote:
                return False, state
        for C, votes in enumerate(state.votes):
            if (C != a):
                for V, vote in enumerate(votes[b]):
                    if vote and V != v:
                        return False, state
        if not any(self.showsSafeAt(state, Q, b, v) for Q in range(numQ)):
            return False, state
        
        dest = State(state)
        dest.votes[a][b][v] = True
        dest.maxBal[a] = b
        return True, dest
    
    def forwardReach(self):
        q = []
        init_state = State()
        q.append(init_state)
        print("adding init")
        
        count = 0
        while len(q) != 0:
            count += 1
            curr = q.pop()
            if curr not in self.R:
                print("curr: \n%s" % curr.str())
                self.R.add(curr)
                for a in range(numA):
                    for b in range(numB):
                        updated, dest = self.increaseMaxBal(curr, a, b)
                        if updated:
                            if dest not in self.R:
                                q.append(dest)
                                print("\tstep: increaseMaxBal(A%d,B%d)" % (a, b))
#                                 print("\tdest:\n%s" % dest.str("\t\t"))
                        for v in range(numV):
                            updated, dest = self.voteFor(curr, a, b, v)
                            if updated:
                                if dest not in self.R:
                                    q.append(dest)
                                    print("\tstep: voteFor(A%d,B%d,V%d)" % (a, b, v))
#                                     print("\tdest:\n%s" % dest.str("\t\t"))
#             if count > 1000:
#                 assert(0)
        
        print("#R = %d" % len(self.R))
        
    
    def print_R_espresso(self):
        global outF, outFile
        outFile = "out_%dA_%dB_%dV" % (numA, numB, numV)
        outF = open(outFile+".pla", 'w')
        
        fprint("# voting: %d acceptors, %d values, %d ballots" % (numA, numV, numB))
        fprint(".i %d" % (numA*(numB+1) + numA*numB*numV))
        fprint(".o 1")
        fprint(".ilb %s" % next(iter(self.R)).str_header_espresso())
        fprint(".ob notR")
        fprint(".phase 0")
        for state in self.R:
            fprint(state.str_espresso() + " 1")
        fprint(".e")
        fprint("")
        print("Now run espresso with the following command:")
        print("./espresso/espresso.linux -o eqntott %s.pla > %s.txt" % (outFile, outFile))
            

def main():
    s = System()
    print("OK")
    s.print_R_espresso()


if __name__ == "__main__":
    main()

   
                        

# Copyright 2014 The ALIVe authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from language import *

class Pred:
  def __repr__(self):
    raise '__repr__ not implemented'

class BoolPred(Pred):
  pass

class ValPred(Pred):
  pass


################################
class PredConst(ValPred):
  def __init__(self, val):
    self.val = val
    assert isinstance(self.val, int)

  def __repr__(self):
    return str(self.val)

  def getTypeConstraints(self):
    ## FIXME
    bits = self.val.bit_length() + int(self.val >= 0)
    return []

  def toSMT(self, state, types):
    return self.val


################################
class PredVar(ValPred):
  def __init__(self, v):
    self.v = v
    assert isinstance(self.v, Instr)

  def __repr__(self):
    return self.v.getName()

  def getTypeConstraints(self):
    return []

  def toSMT(self, state, types):
    return state.eval(self.v, [], [])


################################
class TruePred(BoolPred):
  def __repr__(self):
    return 'true'

  def getTypeConstraints(self):
    return []

  def toSMT(self, state, types):
    return BoolVal(True)


################################
class PredAnd(BoolPred):
  def __init__(self, v1, v2):
    self.v1 = v1
    self.v2 = v2
    assert isinstance(self.v1, BoolPred)
    assert isinstance(self.v2, BoolPred)

  def __repr__(self):
    return '(%s && %s)' % (self.v1, self.v2)

  def getTypeConstraints(self):
    return self.v1.getTypeConstraints() + self.v2.getTypeConstraints()

  def toSMT(self, state, types):
    return And(self.v1.toSMT(state, types), self.v2.toSMT(state, types))


################################
class PredOr(BoolPred):
  def __init__(self, v1, v2):
    self.v1 = v1
    self.v2 = v2
    assert isinstance(self.v1, BoolPred)
    assert isinstance(self.v2, BoolPred)

  def __repr__(self):
    return '(%s || %s)' % (self.v1, self.v2)

  def getTypeConstraints(self):
    return self.v1.getTypeConstraints() + self.v2.getTypeConstraints()

  def toSMT(self, state, types):
    return Or(self.v1.toSMT(state, types), self.v2.toSMT(state, types))


################################
class BinaryBoolPred(BoolPred):
  EQ, NE, Last = range(3)

  opnames = ['==', '!=']

  def __init__(self, op, v1, v2):
    self.op = op
    self.v1 = v1
    self.v2 = v2
    assert self.op >= 0 and self.op < self.Last
    assert isinstance(self.v1, Pred)
    assert isinstance(self.v2, Pred)

  def __repr__(self):
    return '(%s %s %s)' % (self.v1, self.opnames[self.op], self.v2)

  @staticmethod
  def getOpId(name):
    for i in range(BinaryBoolPred.Last):
      if BinaryBoolPred.opnames[i] == name:
        return i
    print 'Unknown boolean operator: ' + name
    exit(-1)

  def getTypeConstraints(self):
    ## FIXME: types eq?
    return self.v1.getTypeConstraints() + self.v2.getTypeConstraints()

  def toSMT(self, state, types):
    v1 = self.v1.toSMT(state, types)
    v2 = self.v2.toSMT(state, types)
    return {
      self.EQ: lambda a,b: a == b,
      self.NE: lambda a,b: a != b,
    }[self.op](v1, v2)


################################
class UnaryValPred(ValPred):
  Not, Neg, Last = range(3)

  opnames = ['~', '-']

  def __init__(self, op, v):
    self.op = op
    self.v = v
    assert self.op >= 0 and self.op < self.Last
    assert isinstance(self.v, ValPred)

  def __repr__(self):
    return '%s%s' % (self.opnames[self.op], self.v)

  @staticmethod
  def getOpId(name):
    for i in range(UnaryValPred.Last):
      if UnaryValPred.opnames[i] == name:
        return i
    print 'Unknown unary operator: ' + name
    exit(-1)

  def getTypeConstraints(self):
    return self.v.getTypeConstraints()

  def toSMT(self, state, types):
    return {
      self.Not: lambda a: ~a,
      self.Neg: lambda a: -a,
    }[self.op](self.v.toSMT(state, types))


################################
class BinaryValPred(ValPred):
  And, Or, Add, Minus, Last = range(5)

  opnames = ['&', '|', '+', '-']

  def __init__(self, op, v1, v2):
    self.op = op
    self.v1 = v1
    self.v2 = v2
    assert self.op >= 0 and self.op < self.Last
    assert isinstance(self.v1, ValPred)
    assert isinstance(self.v2, ValPred)

  def __repr__(self):
    return '(%s %s %s)' % (self.v1, self.opnames[self.op], self.v2)

  def getTypeConstraints(self):
    ## FIXME: types eq?
    return self.v1.getTypeConstraints() + self.v2.getTypeConstraints()

  def toSMT(self, state, types):
    v1 = self.v1.toSMT(state, types)
    v2 = self.v2.toSMT(state, types)
    return {
      self.And:   lambda a,b: a & b,
      self.Or:    lambda a,b: a | b,
      self.Add:   lambda a,b: a + b,
      self.Minus: lambda a,b: a - b,
    }[self.op](v1, v2)

################################
class ValFunction(ValPred):
  width, Last = range(2)
  
  opnames = {
    width: 'width',
  }
  opids = {v:k for k,v in opnames.items()}
  
  num_args = {
    width: 1,
  }
  
  def __init__(self, op, args, type):
    self.op = op
    self.args = args
    self.type = type  ## TODO: implement inference of return type
    assert 0 <= op < self.Last
    for a in args:
      assert isinstance(a, ValPred)

    if self.num_args[op] != len(args):
      raise Exception('Wrong number of arguments to %s (got %d, expected %d)' %
        (self.opnames[op], len(args), self.num_args[op]))
      ## FIXME: subclass exception
  
  def __repr__(self):
    args = [str(a) for a in self.args]
    return '%s(%s)' % (self.opnames[self.op], ', '.join(args))
  
  def getOpName(self): return self.opnames[self.op]
  
  @staticmethod
  def getOpId(name):
    if name in ValFunction.opids:
      return ValFunction.opids[name]

    raise Exception('Unknown function: %s' % name)  ## FIXME: subclass exception
  
  def getTypeConstraints(self):
    return [v.getTypeConstraints() for v in self.args]

  def toSMT(self, state, types):
    args = [v.toSMT(state, types) for v in self.args]
    return {
      self.width: lambda a: BitVecVal(a.sort().size(), a.sort().size())
    }[self.op](*args)
    

################################
class LLVMBoolPred(BoolPred):
  isSignBit, NSWAdd, Last = range(3)

  opnames = {
    isSignBit: 'isSignBit',
    NSWAdd:     'WillNotOverflowSignedAdd',
  }
  opids = {v:k for k, v in opnames.items()}

  num_args = {
    isSignBit: 1,
    NSWAdd:    2,
  }

  def __init__(self, op, args):
    self.op = op
    self.args = args
    if self.num_args[op] != len(args):
      print 'Wrong number of argument to %s (expected %d)' %\
        (self.opnames[op], self.num_args[op])
      exit(-1)
    assert op >= 0 and op < self.Last
    for a in self.args:
      assert isinstance(a, Pred)

  def __repr__(self):
    args = [str(a) for a in self.args]
    return '%s(%s)' % (self.opnames[self.op], ', '.join(args))

  def getOpName(self):
    return self.opnames[self.op]

  @staticmethod
  def getOpId(name):
    try:
      return LLVMBoolPred.opids[name]
    except:
      print 'Unknown boolean predicate: ' + name
      exit(-1)

  def getTypeConstraints(self):
    return [v.getTypeConstraints() for v in self.args]

  def toSMT(self, state, types):
    args = [v.toSMT(state, types) for v in self.args]
    return {
      self.isSignBit: lambda a: a == (1 << (a.sort().size()-1)),
      self.NSWAdd:    lambda a,b: SignExt(1,a)+SignExt(1,b) == SignExt(1, a+b)
    }[self.op](*args)

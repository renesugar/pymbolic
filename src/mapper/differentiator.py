import math
import cmath

import pymbolic
import pymbolic.primitives as primitives
import pymbolic.mapper.evaluator



def map_math_functions_by_name(i, func, pars):
    try:
        f = pymbolic.evaluate(func, {"math": math, "cmath": cmath})
    except pymbolic.mapper.evaluator.UnknownVariableError:
        raise RuntimeError, "No derivative of non-constant function "+str(func)

    def make_f(name):
        return primitives.ElementLookup(primitives.Variable("math"), name)

    if f is math.sin and len(pars) == 1:
        return make_f("cos")(*pars)
    elif f is math.cos and len(pars) == 1:
        return -make_f("sin")(*pars)
    elif f is math.tan and len(pars) == 1:
        return make_f("tan")(*pars)**2+1
    elif f is math.log and len(pars) == 1:
        return primitives.Constant(1)/pars[0]
    elif f is math.exp and len(pars) == 1:
        return make_f("exp")(*pars)
    else:
        raise RuntimeError, "unrecognized function, cannot differentiate"




class DifferentiationMapper:
    def __init__(self, variable, parameters, func_map):
        self.Variable = variable
        self.Parameters = parameters
        self.FunctionMap = func_map

    def map_constant(self, expr):
        return primitives.Constant(0)

    def map_variable(self, expr):
        if expr == self.Variable:
            return primitives.Constant(1)
        elif expr in self.Parameters:
            return expr
        else:
            return primitives.Constant(0)

    def map_call(self, expr):
        return pymbolic.sum(*(
            self.FunctionMap(i, expr.function, expr.parameters)
            * par.invoke_mapper(self)
            for i, par in enumerate(expr.parameters)
            if not self._isc(par)))

    map_subscript = map_variable

    def map_negation(self, expr):
        return -expr.child.invoke_mapper(self)

    def map_sum(self, expr):
        return pymbolic.sum(*(child.invoke_mapper(self)
                              for child in expr.children
                              if not self._isc(child)))

    def map_product(self, expr):
        return pymbolic.sum(*(
            pymbolic.product(*(expr.children[0:i] + 
                             (child.invoke_mapper(self),) +
                             expr.children[i+1:]))
            for i, child in enumerate(expr.children)
            if not self._isc(child)))

    def map_rational(self, expr):
        f = expr.numerator
        g = expr.denominator
        f_const = self._isc(f)
        g_const = self._isc(g)

        if f_const and g_const:
            return primitives.Constant(0)
        elif f_const:
            f = self._eval(f)
            return -f*g.invoke_mapper(self)/g**2
        elif g_const:
            g = self._eval(g)
            return f.invoke_mapper(self)/g
        else:
            return (f.invoke_mapper(self)*g-g.invoke_mapper(self)*f)/g**2

    def map_power(self, expr):
        f = expr.base
        g = expr.exponent
        f_const = self._isc(f)
        g_const = self._isc(g)

        log = primitives.Constant("log")

        if f_const and g_const:
            return primitives.Constant(0)
        elif f_const:
            f = self._eval(f)
            return log(f) * f**g * g.invoke_mapper(self)
        elif g_const:
            g = self._eval(g)
            return g * f**(g-1) * f.invoke_mapper(self)
        else:
            return log(f) * f**g * g.invoke_mapper(self) + \
                   g * f**(g-1) * f.invoke_mapper(self)

    def map_polynomial(self, expr):
        raise NotImplementedError
    
    def _isc(self,subexp):
        return pymbolic.is_constant(subexp, [self.Variable])

    def _eval(self,subexp):
        try:
            return primitives.Constant(pymbolic.evaluate(subexp))
        except KeyError:
            return subexp
  



def differentiate(expression, 
                  variable, 
                  parameters=[],
                  func_mapper=map_math_functions_by_name):
    return expression.invoke_mapper(DifferentiationMapper(variable,
                                                          parameters,
                                                          func_mapper))
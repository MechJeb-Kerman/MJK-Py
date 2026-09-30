from sympy import Eq, solve
from sympy.parsing.sympy_parser import parse_expr


def solve_equation(equation_str):
    # 拆分等号左右两边
    left, right = equation_str.split("=")
    eq = Eq(parse_expr(left), parse_expr(right))

    # 自动识别未知数
    variables = sorted(eq.free_symbols, key=lambda v: v.name)

    # 解方程
    result = solve(eq, variables)
    return result


if __name__ == "__main__":
    eq_str = input("请输入方程，例如 x**2 - 3*x + 2 = 0：")
    result = solve_equation(eq_str)
    print("解为：", result)
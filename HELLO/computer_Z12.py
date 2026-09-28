#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
万能计算器 (Universal Calculator)
==================================
依赖安装:  pip install sympy numpy matplotlib
"""

import sys
import re

# ==================== 依赖检测 ====================
try:
    import sympy as sp
except ImportError:
    sys.exit("缺少 sympy，请先运行:  pip install sympy")

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    np = None
    HAS_NUMPY = False

try:
    import matplotlib
    import matplotlib.pyplot as plt
    HAS_MPL = True
except ImportError:
    plt = None
    HAS_MPL = False


# ==================== 常量 / 函数表 ====================
BASE_LOCALS = {
    "pi": sp.pi, "PI": sp.pi, "tau": 2 * sp.pi,
    "e": sp.E, "E": sp.E, "I": sp.I,
    "oo": sp.oo, "inf": sp.oo,
    "sqrt": sp.sqrt, "root": sp.root,
    "exp": sp.exp, "log": sp.log, "ln": sp.log,
    "sin": sp.sin, "cos": sp.cos, "tan": sp.tan,
    "asin": sp.asin, "acos": sp.acos, "atan": sp.atan,
    "arcsin": sp.asin, "arccos": sp.acos, "arctan": sp.atan,
    "sinh": sp.sinh, "cosh": sp.cosh, "tanh": sp.tanh,
    "Abs": sp.Abs, "abs": sp.Abs,
    "factorial": sp.factorial, "binomial": sp.binomial,
    "gcd": sp.gcd, "lcm": sp.lcm,
    "floor": sp.floor, "ceil": sp.ceiling, "sign": sp.sign,
    "Min": sp.Min, "Max": sp.Max, "gamma": sp.gamma,
    "prime": sp.prime, "Sum": sp.Sum, "Product": sp.Product,
    "Rational": sp.Rational, "Matrix": sp.Matrix,
}
# 部分版本才有的函数
for _name in ("cbrt", "sec", "csc", "cot", "acot", "asec", "acsc"):
    if hasattr(sp, _name):
        BASE_LOCALS[_name] = getattr(sp, _name)


# ==================== 工具函数 ====================
def header(title):
    print()
    print("─" * 48)
    print(f"  {title}")
    print("─" * 48)


def ask(prompt, default=None):
    """读取输入，回车使用默认值"""
    s = input(prompt).strip()
    if s == "" and default is not None:
        return default
    return s


def parse(s, extra=None):
    """把用户输入的字符串转成 sympy 表达式"""
    if s is None or not str(s).strip():
        raise ValueError("表达式为空")
    s = str(s).strip().replace("^", "**")
    local = dict(BASE_LOCALS)
    if extra:
        local.update(extra)
    try:
        return sp.sympify(s, locals=local)
    except Exception:
        # 自动补乘号: 2x -> 2*x, 2(x+1) -> 2*(x+1), (x+1)(x-1) -> (x+1)*(x-1)
        s2 = re.sub(r"(?<=[0-9\)])(?=[a-zA-Z\(])", "*", s)
        return sp.sympify(s2, locals=local)


def show(v, digits=12):
    """显示结果，尽量同时给出精确值和近似值"""
    txt = str(v)
    try:
        if v.is_number and not v.is_Integer:
            n = str(sp.N(v, digits))
            if n != txt:
                return f"{txt}  ≈  {n}"
    except Exception:
        pass
    return txt


# ==================== 1. 表达式计算 ====================
def cmd_expr():
    header("表达式计算")
    print("示例: 2+3*4    sqrt(2)    sin(pi/6)    2^10    (1+2)^3/4")
    print("常量: pi   e   I(虚数)   oo(无穷)")
    s = ask("表达式> ")
    if not s:
        return
    try:
        expr = parse(s)
    except Exception as e:
        print("解析失败:", e)
        return
    try:
        simp = sp.simplify(expr)
    except Exception:
        simp = expr
    print("精确结果 :", simp)
    try:
        print("数值结果 :", sp.N(expr, 15))
    except Exception:
        pass
    try:
        if simp.is_Integer and 0 <= simp <= 2 ** 64:
            n = int(simp)
            print(f"十进制   : {n}")
            print(f"二进制   : {bin(n)}   八进制: {oct(n)}   十六进制: {hex(n)}")
    except Exception:
        pass


# ==================== 2. 解方程 / 方程组 ====================
def cmd_solve():
    header("解方程 / 方程组")
    print("示例: x**2 - 3*x + 2 = 0")
    print("      x + y = 3 ; x - y = 1")
    print("      2*x + 3*y - z = 1 ; x - y = 2 ; y + z = 0")
    s = ask("方程 (多个用 ; 分隔)> ")
    if not s:
        return
    var_s = ask("未知数 (空格分隔, 留空自动识别)> ")

    try:
        eqs = []
        for raw in s.split(";"):
            raw = raw.strip()
            if not raw:
                continue
            if "=" in raw:
                l, r = raw.split("=", 1)
                eqs.append(sp.Eq(parse(l), parse(r)))
            else:
                eqs.append(parse(raw))
    except Exception as e:
        print("解析失败:", e)
        return

    if not eqs:
        print("没有有效方程")
        return

    if var_s:
        syms = [sp.Symbol(n) for n in var_s.replace(",", " ").split()]
    else:
        pool = set()
        for eq in eqs:
            pool |= eq.free_symbols
        syms = sorted(pool, key=lambda v: v.name)

    if not syms:
        print("未识别到未知数")
        return

    print(f"\n求解变量: {', '.join(str(v) for v in syms)}")
    try:
        sol = sp.solve(eqs, syms, dict=True)
    except Exception as e:
        print("求解失败:", e)
        return

    if not sol:
        print("无解，或无法求出解析解")
        return

    for i, d in enumerate(sol, 1):
        prefix = "解:" if len(sol) == 1 else f"解 {i}:"
        parts = [f"{k} = {show(v)}" for k, v in d.items()]
        print(prefix, "   ".join(parts))


# ==================== 3. 一元二次方程 ====================
def cmd_quadratic():
    header("一元二次方程  ax² + bx + c = 0")
    print("系数支持分数和小数，如 1/2 、 0.5 、 sqrt(2)")
    try:
        a = parse(ask("a = ", "1") or "1")
        b = parse(ask("b = ", "0") or "0")
        c = parse(ask("c = ", "0") or "0")
    except Exception as e:
        print("输入有误:", e)
        return

    x = sp.Symbol("x")
    expr = a * x ** 2 + b * x + c
    print(f"\n方程: {expr} = 0")

    if a == 0:
        print("注意: a = 0，这不是一元二次方程。")
        roots = sp.solve(sp.Eq(expr, 0), x)
        print("解:", [show(r) for r in roots] or "无解")
        return

    delta = sp.simplify(b ** 2 - 4 * a * c)
    print(f"判别式 Δ = b²-4ac = {delta}", end="")
    try:
        d = complex(sp.N(delta))
        if abs(d.imag) < 1e-12:
            dr = d.real
            if dr > 1e-12:
                print("   (>0，两个不等实根)")
            elif abs(dr) <= 1e-12:
                print("   (=0，两个相等实根)")
            else:
                print("   (<0，一对共轭复根)")
        else:
            print()
    except Exception:
        print()

    roots = sp.solve(sp.Eq(expr, 0), x)
    if not roots:
        print("无解")
        return
    for i, r in enumerate(roots, 1):
        print(f"x{i} = {show(r)}")

    # 韦达定理
    try:
        print(f"\n韦达定理: x₁+x₂ = {sp.simplify(-b/a)} ,  x₁·x₂ = {sp.simplify(c/a)}")
    except Exception:
        pass


# ==================== 4. 多项式求根 ====================
def cmd_poly():
    header("多项式求根 & 因式分解")
    print("示例: x**3 - 6*x**2 + 11*x - 6")
    s = ask("多项式> ")
    if not s:
        return
    var = ask("变量 (默认 x)> ", "x") or "x"
    x = sp.Symbol(var)

    try:
        poly = parse(s, {var: x})
    except Exception as e:
        print("解析失败:", e)
        return

    try:
        print("因式分解 :", sp.factor(poly))
    except Exception:
        pass

    try:
        P = sp.Poly(poly, x)
        print("次数     :", P.degree())
    except Exception:
        P = None

    roots = None
    if P is not None:
        try:
            rr = sp.roots(P)
            if rr:
                roots = rr
        except Exception:
            pass

    if roots:
        print(f"\n共 {sum(roots.values())} 个根（含重数）:")
        for r, m in roots.items():
            extra = f"   (重数 {m})" if m > 1 else ""
            print(f"  {var} = {show(r)}{extra}")
    else:
        sol = sp.solve(sp.Eq(poly, 0), x)
        if not sol:
            print("未找到根（可能无解析解）")
        else:
            print(f"\n共 {len(sol)} 个根:")
            for r in sol:
                print(f"  {var} = {show(r)}")


# ==================== 5. 微积分 ====================
def cmd_calculus():
    while True:
        header("微积分")
        print("1. 求导    2. 积分    3. 极限    4. 泰勒展开    0. 返回")
        c = ask("选择> ")

        if c == "0":
            return

        elif c == "1":
            try:
                expr = parse(ask("函数 f(x) = "))
                var = ask("对哪个变量求导 (默认 x)> ", "x") or "x"
                v = sp.Symbol(var)
                n = int(ask("阶数 (默认 1)> ", "1") or 1)
                d = sp.diff(expr, v, n)
                print("\n导数 :", d)
                print("化简 :", sp.simplify(d))
            except Exception as e:
                print("出错:", e)

        elif c == "2":
            try:
                expr = parse(ask("被积函数 f(x) = "))
                var = ask("积分变量 (默认 x)> ", "x") or "x"
                v = sp.Symbol(var)
                lo = ask("积分下限 (留空 = 不定积分)> ")
                if lo == "":
                    F = sp.integrate(expr, v)
                    print("\n不定积分 :", F, "+ C")
                else:
                    hi = ask("积分上限> ")
                    res = sp.integrate(expr, (v, parse(lo), parse(hi)))
                    print("\n定积分 :", res)
                    print("近似值 :", sp.N(res, 12))
            except Exception as e:
                print("出错:", e)

        elif c == "3":
            try:
                expr = parse(ask("函数 f(x) = "))
                var = ask("变量 (默认 x)> ", "x") or "x"
                v = sp.Symbol(var)
                p = ask("x → (可用 oo 表示无穷)> ")
                point = parse(p)
                res = sp.limit(expr, v, point)
                print("\n极限 :", res)
            except Exception as e:
                print("出错:", e)

        elif c == "4":
            try:
                expr = parse(ask("函数 f(x) = "))
                var = ask("变量 (默认 x)> ", "x") or "x"
                v = sp.Symbol(var)
                x0 = parse(ask("在 x = ? 处展开 (默认 0)> ", "0") or "0")
                n = int(ask("展开到几阶 (默认 6)> ", "6") or 6)
                print("\n展开式 :", sp.series(expr, v, x0, n))
            except Exception as e:
                print("出错:", e)
        else:
            print("无效选项")


# ==================== 6. 矩阵运算 ====================
def read_matrix(name):
    print(f"输入矩阵 {name}（行间用 ; 分隔，元素用空格分隔）")
    print("  例:  1 2 3; 4 5 6")
    s = ask(f"{name} = ")
    if not s:
        return None
    rows = [r.strip() for r in s.split(";") if r.strip()]
    data = []
    for r in rows:
        data.append([parse(e) for e in r.replace(",", " ").split()])
    if len({len(r) for r in data}) != 1:
        raise ValueError("矩阵每行元素个数必须相同")
    return sp.Matrix(data)


def cmd_matrix():
    while True:
        header("矩阵运算")
        print("1. 加法 A+B          2. 乘法 A*B")
        print("3. 转置 Aᵀ           4. 行列式 |A|")
        print("5. 逆矩阵 A⁻¹        6. 秩 rank(A)")
        print("7. 特征值/特征向量    8. 解线性方程组 Ax=b")
        print("9. 行最简形 rref     0. 返回")
        c = ask("选择> ")
        if c == "0":
            return

        try:
            if c in ("1", "2", "8"):
                A = read_matrix("A")
                if A is None:
                    continue
                if c == "1":
                    B = read_matrix("B")
                    if B is None:
                        continue
                    print("\nA + B =")
                    sp.pprint(A + B)
                elif c == "2":
                    B = read_matrix("B")
                    if B is None:
                        continue
                    print("\nA * B =")
                    sp.pprint(A * B)
                else:
                    print("输入常数列向量 b（用 ; 分隔）")
                    b = read_matrix("b")
                    if b is None:
                        continue
                    sol = A.solve(b)
                    print("\n解 x =")
                    sp.pprint(sol)

            elif c in ("3", "4", "5", "6", "7", "9"):
                A = read_matrix("A")
                if A is None:
                    continue
                if c == "3":
                    print("\nAᵀ =")
                    sp.pprint(A.T)
                elif c == "4":
                    print("\n|A| =", A.det())
                elif c == "5":
                    if A.det() == 0:
                        print("\n矩阵不可逆（行列式为 0）")
                    else:
                        print("\nA⁻¹ =")
                        sp.pprint(A.inv())
                elif c == "6":
                    print("\nrank(A) =", A.rank())
                elif c == "7":
                    print("\n特征值 :", A.eigenvals())
                    print("特征向量 :")
                    for val, mult, vecs in A.eigenvects():
                        print(f"  λ = {val} (重数 {mult})")
                        for v in vecs:
                            sp.pprint(v)
                elif c == "9":
                    print("\n行最简形 rref =")
                    sp.pprint(A.rref()[0])
            else:
                print("无效选项")
        except Exception as e:
            print("出错:", e)


# ==================== 7. 统计计算 ====================
def cmd_stats():
    header("统计计算")
    s = ask("输入一组数据（空格或逗号分隔）> ")
    if not s:
        return
    try:
        data = [float(x) for x in s.replace(",", " ").split()]
    except ValueError:
        print("数据格式错误")
        return
    n = len(data)
    if n == 0:
        return

    sd = sorted(data)
    total = sum(data)
    mean = total / n
    median = sd[n // 2] if n % 2 else (sd[n // 2 - 1] + sd[n // 2]) / 2

    from collections import Counter
    cnt = Counter(data)
    maxc = max(cnt.values())
    modes = [k for k, v in cnt.items() if v == maxc] if maxc > 1 else []

    var_p = sum((x - mean) ** 2 for x in data) / n
    var_s = sum((x - mean) ** 2 for x in data) / (n - 1) if n > 1 else float("nan")

    print(f"\n数据个数   : {n}")
    print(f"总和       : {total:g}")
    print(f"最小值     : {min(data):g}")
    print(f"最大值     : {max(data):g}")
    print(f"极差       : {max(data) - min(data):g}")
    print(f"平均值     : {mean:g}")
    print(f"中位数     : {median:g}")
    print(f"众数       : {', '.join(f'{m:g}' for m in modes) if modes else '无'}")
    print(f"总体方差   : {var_p:g}     总体标准差: {var_p ** 0.5:g}")
    if n > 1:
        print(f"样本方差   : {var_s:g}     样本标准差: {var_s ** 0.5:g}")
    if all(x > 0 for x in data):
        geo = 1.0
        for x in data:
            geo *= x
        print(f"几何平均数 : {geo ** (1 / n):g}")
    if all(x != 0 for x in data):
        print(f"调和平均数 : {n / sum(1 / x for x in data):g}")


# ==================== 8. 代数化简 ====================
def cmd_algebra():
    while True:
        header("代数化简")
        print("1. 化简      2. 展开      3. 因式分解")
        print("4. 通分      5. 部分分式  6. 代入求值")
        print("7. 合并同类项   0. 返回")
        c = ask("选择> ")
        if c == "0":
            return

        try:
            if c == "6":
                expr = parse(ask("表达式> "))
                sub_s = ask("代入, 如 x=2, y=3> ")
                subs = {}
                for pair in sub_s.replace(";", ",").split(","):
                    if "=" not in pair:
                        continue
                    k, v = pair.split("=", 1)
                    subs[sp.Symbol(k.strip())] = parse(v.strip())
                res = expr.subs(subs)
                print("\n结果 :", res)
                try:
                    print("数值 :", sp.N(res, 12))
                except Exception:
                    pass
            else:
                expr = parse(ask("表达式> "))
                if c == "1":
                    print("\n化简结果 :", sp.simplify(expr))
                elif c == "2":
                    print("\n展开结果 :", sp.expand(expr))
                elif c == "3":
                    print("\n因式分解 :", sp.factor(expr))
                elif c == "4":
                    print("\n通分结果 :", sp.together(expr))
                elif c == "5":
                    print("\n部分分式 :", sp.apart(expr))
                elif c == "7":
                    var = ask("对哪个变量合并 (默认 x)> ", "x") or "x"
                    print("\n结果 :", sp.collect(expr, sp.Symbol(var)))
                else:
                    print("无效选项")
        except Exception as e:
            print("出错:", e)


# ==================== 9. 函数绘图 ====================
def cmd_plot():
    if not HAS_MPL or not HAS_NUMPY:
        print("需要 numpy 和 matplotlib:  pip install numpy matplotlib")
        return
    header("函数绘图")
    s = ask("函数表达式 f(x) = ")
    if not s:
        return

    x = sp.Symbol("x")
    try:
        expr = parse(s, {"x": x})
    except Exception as e:
        print("解析失败:", e)
        return

    try:
        xmin = float(ask("x 下限 (默认 -10)> ", "-10") or -10)
        xmax = float(ask("x 上限 (默认 10)> ", "10") or 10)
    except ValueError:
        print("范围必须是数字")
        return

    f = sp.lambdify(x, expr, modules=["numpy"])
    xs = np.linspace(xmin, xmax, 2000)
    with np.errstate(all="ignore"):
        ys = f(xs)

    ys = np.asarray(ys)
    if np.iscomplexobj(ys):
        if np.max(np.abs(ys.imag)) > 1e-9:
            print("注意: 函数在部分区间为复数，只绘制实部")
        ys = ys.real
    ys = ys.astype(float)
    ys[~np.isfinite(ys)] = np.nan

    plt.figure(figsize=(9, 5.5))
    plt.plot(xs, ys, linewidth=1.6, label=f"f(x) = {s}")
    plt.axhline(0, color="black", linewidth=0.8)
    plt.axvline(0, color="black", linewidth=0.8)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.title(s)
    plt.xlabel("x")
    plt.ylabel("y")
    plt.tight_layout()
    plt.savefig("plot.png", dpi=120)
    print("图像已保存为 plot.png")
    try:
        plt.show()
    except Exception:
        pass
    plt.close()


# ==================== 10. 数论工具 ====================
def cmd_number():
    while True:
        header("数论工具")
        print("1. 质因数分解        2. 最大公约数 / 最小公倍数")
        print("3. 判断质数          4. 第 n 个质数 / 下一个质数")
        print("5. 欧拉函数 φ(n)     6. 阶乘 / 组合数 / 排列数")
        print("7. 约数列表          0. 返回")
        c = ask("选择> ")
        if c == "0":
            return

        try:
            if c == "1":
                n = int(ask("n = "))
                f = sp.factorint(n)
                parts = " × ".join(
                    f"{p}^{k}" if k > 1 else f"{p}" for p, k in sorted(f.items())
                )
                print(f"\n{n} = {parts}")
                # 展示展开形式
                expanded = " × ".join(str(p) for p, k in sorted(f.items()) for _ in range(k))
                print(f"即: {expanded}")

            elif c == "2":
                a = int(ask("a = "))
                b = int(ask("b = "))
                print(f"\ngcd({a}, {b}) = {sp.gcd(a, b)}")
                print(f"lcm({a}, {b}) = {sp.lcm(a, b)}")

            elif c == "3":
                n = int(ask("n = "))
                print(f"\n{n} " + ("是质数" if sp.isprime(n) else "不是质数"))

            elif c == "4":
                print("1. 第 n 个质数    2. 大于 n 的下一个质数")
                k = ask("选择> ")
                n = int(ask("n = "))
                if k == "1":
                    print(f"\n第 {n} 个质数是 {sp.prime(n)}")
                else:
                    print(f"\n大于 {n} 的最小质数是 {sp.nextprime(n)}")

            elif c == "5":
                n = int(ask("n = "))
                print(f"\nφ({n}) = {sp.totient(n)}")

            elif c == "6":
                print("1. 阶乘 n!    2. 组合数 C(n,k)    3. 排列数 P(n,k)")
                k = ask("选择> ")
                n = int(ask("n = "))
                if k == "1":
                    print(f"\n{n}! = {sp.factorial(n)}")
                else:
                    r = int(ask("k = "))
                    if k == "2":
                        print(f"\nC({n},{r}) = {sp.binomial(n, r)}")
                    else:
                        print(f"\nP({n},{r}) = {sp.factorial(n) // sp.factorial(n - r)}")

            elif c == "7":
                n = int(ask("n = "))
                d = sp.divisors(n)
                print(f"\n{n} 的约数: {d}")
                print(f"约数个数: {len(d)}    约数之和: {sum(d)}")
            else:
                print("无效选项")
        except Exception as e:
            print("出错:", e)


# ==================== 11. 进制转换 ====================
DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"


def to_base(n, b):
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    out = ""
    while n:
        out = DIGITS[n % b] + out
        n //= b
    return sign + out


def cmd_base():
    header("进制转换")
    print("1. 十进制 → 其他进制")
    print("2. 任意进制 → 十进制")
    print("3. 任意进制 → 任意进制")
    c = ask("选择> ")

    try:
        if c == "1":
            n = int(ask("十进制数 n = "))
            print(f"\n二进制   : {to_base(n, 2)}")
            print(f"八进制   : {to_base(n, 8)}")
            print(f"十六进制 : {to_base(n, 16)}")
            b = int(ask("还想转成几进制? (2-36, 回车跳过)> ", "0") or 0)
            if 2 <= b <= 36:
                print(f"{b} 进制  : {to_base(n, b)}")

        elif c == "2":
            s = ask("数字> ")
            b = int(ask("它是几进制? (2-36)> "))
            print(f"\n十进制 = {int(s, b)}")

        elif c == "3":
            s = ask("数字> ")
            b1 = int(ask("原进制 (2-36)> "))
            b2 = int(ask("目标进制 (2-36)> "))
            n = int(s, b1)
            print(f"\n{to_base(n, b2)}")

        else:
            print("无效选项")
    except Exception as e:
        print("出错:", e)


# ==================== 12. 求和 / 连乘 ====================
def cmd_series():
    header("求和 / 连乘")
    print("1. 求和 Σ      2. 连乘 Π      0. 返回")
    c = ask("选择> ")
    if c not in ("1", "2"):
        return

    s = ask("通项表达式 (如 n**2, 1/n!, x**n/n!)> ")
    var = ask("变量名 (默认 n)> ", "n") or "n"
    v = sp.Symbol(var)
    lo_s = ask("起始值 (如 1)> ")
    hi_s = ask("结束值 (如 10 或 oo)> ")

    try:
        expr = parse(s, {var: v})
        lo = parse(lo_s)
        hi = parse(hi_s)
        if c == "1":
            res = sp.summation(expr, (v, lo, hi))
            print(f"\nΣ({var}={lo}..{hi}) {expr} = {res}")
        else:
            res = sp.product(expr, (v, lo, hi))
            print(f"\nΠ({var}={lo}..{hi}) {expr} = {res}")
        try:
            print("近似值 :", sp.N(res, 12))
        except Exception:
            pass
    except Exception as e:
        print("出错:", e)


# ==================== 主菜单 ====================
MENU = """
╔════════════════════════════════════════════════╗
║               万  能  计  算  器                ║
╠════════════════════════════════════════════════╣
║   1. 表达式计算            2. 解方程 / 方程组   ║
║   3. 一元二次方程          4. 多项式求根        ║
║   5. 微积分                6. 矩阵运算          ║
║   7. 统计计算              8. 代数化简          ║
║   9. 函数绘图             10. 数论工具          ║
║  11. 进制转换             12. 求和 / 连乘       ║
║                                                ║
║   0. 退出                                      ║
╚════════════════════════════════════════════════╝
"""

ACTIONS = {
    "1": cmd_expr,
    "2": cmd_solve,
    "3": cmd_quadratic,
    "4": cmd_poly,
    "5": cmd_calculus,
    "6": cmd_matrix,
    "7": cmd_stats,
    "8": cmd_algebra,
    "9": cmd_plot,
    "10": cmd_number,
    "11": cmd_base,
    "12": cmd_series,
}


def main():
    print("欢迎使用万能计算器！(输入 0 退出)")
    while True:
        print(MENU)
        c = ask("请选择 > ")
        if c in ("0", "q", "quit", "exit"):
            print("再见！")
            break
        action = ACTIONS.get(c)
        if action is None:
            print("无效选项，请重新选择")
            continue
        try:
            action()
        except KeyboardInterrupt:
            print("\n(已取消当前操作)")
        except Exception as e:
            print(f"出错了: {e}")


if __name__ == "__main__":
    main()
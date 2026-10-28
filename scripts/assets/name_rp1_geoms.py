"""Give RP1's collision geoms names so UniLab can bind friction writes.

rpo.xml names no geoms, and UniLab's SuperMimic context event needs a geom list
to randomise foot friction.  We name the non-visual mesh geoms ``<mesh>_collision``
and write that list into robot_rp1.COLLISION_GEOM_NAMES.

    python name_rp1_geoms.py --xml <rpo_supermimic.xml> --robot-py <robot_rp1.py>
"""
import argparse
import re

GEOM = re.compile(r'<geom\s+(?P<attrs>[^>]*?)/>')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--robot-py", required=True)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    text = open(args.xml, encoding="utf-8").read()
    names = []

    def repl(match):
        attrs = match.group("attrs")
        if 'mesh="' not in attrs or 'name="' in attrs:
            return match.group(0)
        if 'class="visualgeom"' in attrs:
            return match.group(0)
        mesh = re.search(r'mesh="([^"]+)"', attrs).group(1)
        name = f"{mesh}_collision"
        names.append(name)
        return f'<geom name="{name}" {attrs}/>'

    new_text, count = GEOM.subn(repl, text)
    print(f"named {count} collision geoms")
    print("first five:", names[:5])

    if args.dry_run:
        return

    open(args.xml, "w", encoding="utf-8").write(new_text)

    # rewrite COLLISION_GEOM_NAMES in the robot profile
    py = open(args.robot_py, encoding="utf-8").read()
    block = "COLLISION_GEOM_NAMES = (\n" + "".join(f'    "{n}",\n' for n in names) + ")"
    new_py, n = re.subn(
        r"COLLISION_GEOM_NAMES = None|COLLISION_GEOM_NAMES = \(.*?\n\)",
        block,
        py,
        flags=re.S,
    )
    if n != 1:
        raise SystemExit(f"expected to replace COLLISION_GEOM_NAMES once, got {n}")
    open(args.robot_py, "w", encoding="utf-8").write(new_py)
    print(f"wrote {len(names)} names into {args.robot_py}")


if __name__ == "__main__":
    main()

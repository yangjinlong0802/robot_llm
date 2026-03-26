# -*- coding: utf-8 -*-
"""
ADP 吐液（全部吐出）
"""
import sys

dst_path = r"/home/maic/10-robotgui/src/vertical_grab/code/robot_arm"
sys.path.insert(0, dst_path)

from Class.Class_ADP import ADP

ADP_PORT = '/dev/hand'


def main():
    print("=" * 50)
    print("ADP 吐液（全部吐出）")
    print("=" * 50)

    print(f"\n串口: {ADP_PORT}")

    adp = ADP(port=ADP_PORT)

    print("\n正在吐液...")
    ret = adp.dispense_all()

    if ret:
        print("吐液成功!")
    else:
        print("吐液失败")

    adp.close()


if __name__ == "__main__":
    main()

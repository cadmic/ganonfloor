#!/usr/bin/env python3

import argparse
import struct
import sys

SHT_MAX = 0x7FFF
COLPOLY_NORMAL_FRAC = 1.0 / SHT_MAX

ACTOR_NAMES = {
    0x000A: 'En_Box',
    0x003F: 'Bg_Dodoago',
    0x0058: 'Bg_Ddan_Jd',
    0x0059: 'Bg_Breakwall',
    0x012A: 'Obj_Switch',
}

VC = False

def seek(f, addr):
    if VC:
        f.seek(addr - 0x80000000 + 0xE74000)
    else:
        f.seek(addr - 0x80000000)

def read_s8(f):
    [x] = struct.unpack('>b', f.read(1))
    return x

def read_u8(f):
    [x] = struct.unpack('>B', f.read(1))
    return x

def read_s16(f):
    [x] = struct.unpack('>h', f.read(2))
    return x

def read_u16(f):
    [x] = struct.unpack('>H', f.read(2))
    return x

def read_s32(f):
    [x] = struct.unpack('>i', f.read(4))
    return x

def read_u32(f):
    [x] = struct.unpack('>I', f.read(4))
    return x

def read_f32(f):
    [x] = struct.unpack('>f', f.read(4))
    return x

def print_bgactor(f, i):
    seek(f, 0x801C9520 + 0x54 + i * 0x64)
    addr = read_u32(f)
    col_header = read_u32(f)
    poly_start_index = read_u16(f)
    ceiling_list = read_u16(f)
    wall_list = read_u16(f)
    floor_list = read_u16(f)
    vertex_start_index = read_u16(f)

    seek(f, addr)
    actor_id = read_u16(f)
    actor_cat = read_u8(f)
    print('bgactor {}: name={} id={:04X} cat={} addr={:08X} vertex_start={} ({:08X}) poly_start={} ({:08X})'.format(
        i,  ACTOR_NAMES[actor_id], actor_id, actor_cat, addr,
        vertex_start_index, 0x8025B7F0 + vertex_start_index * 0x6,
        poly_start_index, 0x8025C3F0 + poly_start_index * 0x10))

def print_bgactors(f):
    for i in range(48):
        print_bgactor(f, i)

def read_vertex(f, index):
    seek(f, 0x8037E9A8 + index * 0x6)
    x = read_s16(f)
    y = read_s16(f)
    z = read_s16(f)
    return (x, y, z)
    print('  vertex {}: ({},{},{})'.format(index, x, y, z))

def print_poly(f, addr):
    seek(f, addr)
    poly_type = read_u16(f)
    i1 = read_u16(f)
    i2 = read_u16(f)
    i3 = read_u16(f)
    nx = read_s16(f)
    ny = read_s16(f)
    nz = read_s16(f)
    dist = read_s16(f)

    v1 = read_vertex(f, i1 & 0x1FFF)
    v2 = read_vertex(f, i2 & 0x1FFF)
    v3 = read_vertex(f, i3)

    print('      type: 0x{:04X}'.format(poly_type))
    print('      flags: 0x{:01X}'.format(i1 >> 13))
    print('      v1: ({}, {}, {})'.format(v1[0], v1[1], v1[2]))
    print('      v2: ({}, {}, {})'.format(v2[0], v2[1], v2[2]))
    print('      v3: ({}, {}, {})'.format(v3[0], v3[1], v3[2]))
    print('      nx: {:.4}'.format(nx * COLPOLY_NORMAL_FRAC))
    print('      ny: {:.4}'.format(ny * COLPOLY_NORMAL_FRAC))
    print('      nz: {:.4}'.format(nz * COLPOLY_NORMAL_FRAC))
    print('      dist: {}'.format(dist, dist))

def print_poly_list(f, node):
    while node != 0xFFFF:
        node_addr = 0x8025F244 + node * 0x4
        seek(f, node_addr)
        poly_id = read_u16(f)
        next_node = read_u16(f)

        poly_addr = 0x803704B8 + poly_id * 0x10
        seek(f, poly_addr)
        poly_type = read_u16(f)

        seek(f, 0x80370308 + poly_type * 0x8)
        data0 = read_u32(f)
        data1 = read_u32(f)

        exit_index = (data0 >> 8) & 0x1F

        print('    node={:04X} ({:08X}) poly_id={:04X} ({:08X}) type={:04X} exit_index={:03X}'.format(
            node, node_addr, poly_id, poly_addr, poly_type, exit_index))
        print_poly(f, poly_addr)
        node = next_node

def print_sectors(f):
    seek(f, 0x801C9520 + 0x4)
    min_x = read_f32(f)
    min_y = read_f32(f)
    min_z = read_f32(f)
    seek(f, 0x801C9520 + 0x28)
    length_x = read_f32(f)
    length_y = read_f32(f)
    length_z = read_f32(f)
    for z in range(16):
        for y in range(4):
            for x in range(16):
                index = x + y * 16 + z * 16 * 4
                seek(f, 0x802747F0 + index * 0x6)
                floor = read_u16(f)
                wall = read_u16(f)
                ceiling = read_u16(f)
                print('sector {}: x=[{},{}] y=[{},{}] z=[{},{}]'.format(
                    index,
                    min_x + x * length_x, min_x + (x + 1) * length_x,
                    min_y + y * length_y, min_y + (y + 1) * length_y,
                    min_z + z * length_z, min_z + (z + 1) * length_z))
                print('  floors:')
                print_poly_list(f, floor)
                print('  walls:')
                print_poly_list(f, wall)
                print('  ceiling:')
                print_poly_list(f, ceiling)

def main():
    parser = argparse.ArgumentParser(description='Ganonfloor memory dump viewer')
    parser.add_argument('filename', metavar='FILE', type=str, nargs='?', help='RAM dump')
    parser.add_argument('--vc', action='store_true', help='Interpret as VC MEM1 dump')

    args = parser.parse_args()

    global VC
    VC = args.vc

    with open(args.filename, 'rb') as f:
        # print_bgactors(f)
        print_sectors(f)

if __name__ == '__main__':
    main()

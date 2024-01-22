#!/usr/bin/env python3

import argparse
import struct
import sys

SHT_MAX = 0x7FFF
COLPOLY_NORMAL_FRAC = 1.0 / SHT_MAX

COL_CTX = 0x801C9520

ACTOR_NAMES = {
    0x000A: 'En_Box',
    0x003F: 'Bg_Dodoago',
    0x0058: 'Bg_Ddan_Jd',
    0x0059: 'Bg_Breakwall',
    0x012A: 'Obj_Switch',
}

args = None

def seek(f, addr):
    if args.vc:
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

class ColData:
    def __init__(self, f):
            seek(f, COL_CTX)
            self.col_header = read_u32(f)
            self.min_x = read_f32(f)
            self.min_y = read_f32(f)
            self.min_z = read_f32(f)

            seek(f, COL_CTX + 0x1C)
            self.amount_x = read_u32(f)
            self.amount_y = read_u32(f)
            self.amount_z = read_u32(f)
            self.length_x = read_f32(f)
            self.length_y = read_f32(f)
            self.length_z = read_f32(f)

            seek(f, COL_CTX + 0x40)
            self.lookup_tbl = read_u32(f)
            self.node_max = read_u16(f)
            self.node_count = read_u16(f)
            self.node_tbl = read_u32(f)
            self.poly_check_tbl = read_u32(f)

            seek(f, self.col_header + 0x0C)
            self.num_vertices = read_u32(f)
            self.vertex_tbl = read_u32(f)
            self.num_polys = read_u32(f)
            self.poly_tbl = read_u32(f)
            self.surface_type_tbl = read_u32(f)

def print_bgactor(f, i):
    seek(f, COL_CTX + 0x50 + 0x13F0)
    dyna_poly_tbl = read_u32(f)
    dyna_vertex_tbl = read_u32(f)

    seek(f, COL_CTX + 0x54 + i * 0x64)
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
        vertex_start_index, dyna_poly_tbl + vertex_start_index * 0x6,
        poly_start_index, dyna_poly_tbl + poly_start_index * 0x10))

def print_bgactors(f):
    for i in range(48):
        print_bgactor(f, i)

def read_vertex(f, col_data, index):
    seek(f, col_data.vertex_tbl + index * 0x6)
    x = read_s16(f)
    y = read_s16(f)
    z = read_s16(f)
    return (x, y, z)
    print('  vertex {}: ({},{},{})'.format(index, x, y, z))

def print_poly(f, col_data, addr):
    seek(f, addr)
    poly_type = read_u16(f)
    i1 = read_u16(f)
    i2 = read_u16(f)
    i3 = read_u16(f)
    nx = read_s16(f)
    ny = read_s16(f)
    nz = read_s16(f)
    dist = read_s16(f)

    v1 = read_vertex(f, col_data, i1 & 0x1FFF)
    v2 = read_vertex(f, col_data, i2 & 0x1FFF)
    v3 = read_vertex(f, col_data, i3)

    print('      type: 0x{:04X}'.format(poly_type))
    print('      flags: 0x{:01X}'.format(i1 >> 13))
    print('      v1: ({}, {}, {})'.format(v1[0], v1[1], v1[2]))
    print('      v2: ({}, {}, {})'.format(v2[0], v2[1], v2[2]))
    print('      v3: ({}, {}, {})'.format(v3[0], v3[1], v3[2]))
    print('      nx: {:.4}'.format(nx * COLPOLY_NORMAL_FRAC))
    print('      ny: {:.4}'.format(ny * COLPOLY_NORMAL_FRAC))
    print('      nz: {:.4}'.format(nz * COLPOLY_NORMAL_FRAC))
    print('      dist: {}'.format(dist, dist))

def print_poly_list(f, col_data, node):
    visited = set()

    while node != 0xFFFF:
        if node in visited:
            print('    node={:04X} <loop>'.format(node))
            break
        visited.add(node)

        node_addr = col_data.node_tbl + node * 0x4
        seek(f, node_addr)
        poly_id = read_u16(f)
        next_node = read_u16(f)

        poly_addr = col_data.poly_tbl + poly_id * 0x10
        seek(f, poly_addr)
        poly_type = read_u16(f)

        seek(f, col_data.surface_type_tbl + poly_type * 0x8)
        data0 = read_u32(f)
        data1 = read_u32(f)

        exit_index = (data0 >> 8) & 0x1F

        print('    node={:04X} ({:08X}) poly_id={:04X} ({:08X}) type={:04X} exit_index={:03X}'.format(
            node, node_addr, poly_id, poly_addr, poly_type, exit_index))
        if args.print_polys:
            print_poly(f, col_data, poly_addr)
        node = next_node

def print_sectors(f, col_data):
    for z in range(col_data.amount_z):
        for y in range(col_data.amount_y):
            for x in range(col_data.amount_x):
                index = x + y * col_data.amount_x + z * col_data.amount_x * col_data.amount_y
                seek(f, col_data.lookup_tbl + index * 0x6)
                floor = read_u16(f)
                wall = read_u16(f)
                ceiling = read_u16(f)
                print('sector {}: x=[{},{}] y=[{},{}] z=[{},{}]'.format(
                    index,
                    col_data.min_x + x * col_data.length_x,
                    col_data.min_x + (x + 1) * col_data.length_x,
                    col_data.min_y + y * col_data.length_y,
                    col_data.min_y + (y + 1) * col_data.length_y,
                    col_data.min_z + z * col_data.length_z,
                    col_data.min_z + (z + 1) * col_data.length_z))
                print('  floors:')
                print_poly_list(f, col_data, floor)
                print('  walls:')
                print_poly_list(f, col_data, wall)
                print('  ceiling:')
                print_poly_list(f, col_data, ceiling)

def main():
    parser = argparse.ArgumentParser(description='Ganonfloor memory dump viewer')
    parser.add_argument('filename', metavar='FILE', type=str, nargs='?', help='RAM dump')
    parser.add_argument('--vc', action='store_true', help='Interpret as VC MEM1 dump')
    parser.add_argument('--print-polys', action='store_true', help='Print polygon data')

    global args
    args = parser.parse_args()

    with open(args.filename, 'rb') as f:
        col_data = ColData(f)
        # print_bgactors(f)
        print_sectors(f, col_data)

if __name__ == '__main__':
    main()

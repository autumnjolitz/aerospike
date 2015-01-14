# -*- coding: utf-8 -*-
'''
Convert data types to the Python equivalents.
'''
CL_NULL = 0x00
CL_INT = 0x01
CL_FLOAT = 2
CL_STR = 0x03
CL_BLOB = 0x04

CL_TIMESTAMP = 5
CL_DIGEST = 6
CL_JAVA_BLOB = 7
CL_CSHARP_BLOB = 8
CL_PYTHON_BLOB = 9

CL_RUBY_BLOB = 10
CL_UNKNOWN = 666666


convert_to_str = \
    lambda bin, ffi: ffi.string(bin.object.u.str, bin.object.size)

void_ptr = \
    lambda bin, ffi: bin


def convert_float_double(bin, ffi):
    size = int(bin.object.size[0])
    if size == 4:
        return ffi.cast('float *', bin.object.blob)[0]
    if size == 8:
        return ffi.cast('double *', bin.object.blob)[0]
    raise ValueError(
        "Unrecognized size {0} bytes for casting to datatype!".format(
            size))


EXTRACT_METHODS = {
    CL_NULL: lambda x, ffi: None,
    CL_INT: lambda x, ffi: x.object.u.i64,
    CL_FLOAT: convert_float_double,
    CL_STR: convert_to_str,
    CL_TIMESTAMP: convert_to_str,
    CL_DIGEST: void_ptr,
    CL_BLOB: void_ptr,
    CL_JAVA_BLOB: void_ptr,
    CL_CSHARP_BLOB: void_ptr,
    CL_PYTHON_BLOB: void_ptr,
    CL_RUBY_BLOB: void_ptr,
    CL_UNKNOWN: void_ptr,
}


def get_value(bin, bin_type, ffi):
    return EXTRACT_METHODS[bin_type](bin, ffi)


def get_bin_name(bin, ffi):
    '''A bin is allocated as char[32]. So copy up to using ff.string.
    '''
    return ffi.string(bin.bin_name, 32)


def type_filter(type_id, ffi):
    def test_type(bin):
        return bin and bin.object and bin.object.type == type_id
    return test_type


def bin_name_filter(name, ffi):
    def test_name(bin):
        return bin and ffi.string(bin.bin_name) == name
    return test_name


def chain_filters(*filters):
    def generator(source):
        for item in source:
            for test in filters:
                if not test(item):
                    break
            else:
                yield item
    return generator

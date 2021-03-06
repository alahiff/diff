#!/usr/bin/python
import h5py
import numpy as np
import sys

# compare the contents of two datasets
def compare_datasets(file1, dataset1, file2, dataset2):
    np_dataset1 = np.array(file1.get(dataset1))
    np_dataset2 = np.array(file2.get(dataset2))
    difference = np.subtract(np_dataset1, np_dataset2)
    if not np.all(difference == 0):
        return False
    return True

# compare the values of two attributes
def compare_attributes(file1, file2, name):
    value1 = file1.attrs.get(name)
    value2 = file2.attrs.get(name)
    if value1 != value2:
        return False
    return True

# load attributes
def read_attributes(hval):
    attr = {}
    for k in hval.attrs:
        attr[k] = type(hval.attrs[k])
    return attr

# returns summary of group. 
# the only element for comparison here is the group's attributes
def read_group(hval):
    desc = {}
    desc["attr"] = read_attributes(hval)
    desc["htype"] = "group"
    return desc

# returns summary of dataset
# the only elements for comparison here are the dataset's attributes,
#   and the dataset dtype
def read_data(hval):
    desc = {}
    desc["attr"] = read_attributes(hval)
    desc["htype"] = "dataset"
    desc["dtype"] = type(hval[()])
    return desc

# creates and returns a summary description for every element in a group
def evaluate_group(path, grp):
    desc = {}
    for k,v in grp.items():
        if isinstance(v, h5py.Dataset):
            desc[k] = read_data(v)
        elif isinstance(v, h5py.Group):
            desc[k] = read_group(v)
        else:
            fatal_error("Unknown h5py type: %s (%s -- %s)"% (type(v), path, k))
    return desc

def diff_groups(file1, grp1, file2, grp2, path):
    print("------------------------------")
    print("Examining " + path)
    desc1 = evaluate_group(path, grp1)
    desc2 = evaluate_group(path, grp2)
    common = []
    differs = False
    for k in desc1:
        if k in desc2:
            common.append(k)
        else:
            print("** Element '%s' only in '%s' (DIFF_UNIQUE_A)**" % (k, file1))
            differs = True
    for k in desc2:
        if k not in desc1:
            print("** Element '%s' only in '%s' (DIFF_UNIQUE_B)**" % (k, file2))
            differs = True
    for i in range(len(common)):
        name = common[i]
        print("\t" + name)
        # compare types
        h1 = desc1[name]["htype"]
        h2 = desc2[name]["htype"]
        if h1 != h2:
            print("**  Different element types: '%s' and '%s' (DIFF_OBJECTS)" % (h1, h2))
            differs = True
            continue    # different hdf5 types -- don't try to compare further
        if h1 != "dataset" and h1 != "group":
            print("WARNING: element is not a recognized type (%s) and isn't being evaluated" % h1)
            continue
        # handle datasets first
        if desc1[name]["htype"] != "dataset":
            continue
        # compare data
        fld1 = desc1[name]
        if desc1[name]["dtype"] != desc2[name]["dtype"]:
            d1 = desc1[name]["dtype"]
            d2 = desc2[name]["dtype"]
            print("** Different dtypes: '%s' and '%s' (DIFF_DTYPE)**" % (d1, d2))
            differs = True
        d1name = '%s/%s' % (grp1.name, name)
        d2name = '%s/%s' % (grp2.name, name)
        if grp1.get(d1name).shape != grp2.get(d2name).shape:
            print("** Different shapes: '%s' has different shapes (DIFF_DATA_SHAPE)**" % name)
            differs = True
        else:
            if not compare_datasets(grp1, d1name, grp2, d2name):
                print("** Different data: '%s' (DIFF_DATA_VALUE)**" % name)
                differs = True
        # compare attributes
        for k in desc1[name]["attr"]:
            if k not in desc2[name]["attr"]:
                print("** Attribute '%s' only in '%s' (DIFF_UNIQ_ATTR_A)**" % (k, file1))
                differs = True
        for k in desc2[name]["attr"]:
            if k not in desc1[name]["attr"]:
                print("** Attribute '%s' only in '%s' (DIFF_UNIQ_ATTR_B)**" % (k, file2))
                differs = True
        for k in desc1[name]["attr"]:
            if k in desc2[name]["attr"]:
                v = desc1[name]["attr"][k]
                v2 = desc2[name]["attr"][k]
                if v != v2:
                    print("** Attribute '%s' has different type: '%s' and '%s' (DIFF_ATTR_DTYPE)" % (k, v, v2))
                    differs = True
                else:
                    result = compare_attributes(grp1, grp2, k)
                    if not result:
                        print("** Attribute '%s' value(s) different (DIFF_ATTR_VALUE)" % k)
                        differs = True
    for i in range(len(common)):
        name = common[i]
        # compare types
        if desc1[name]["htype"] != desc2[name]["htype"]:
            continue    # problem already reported
        if desc1[name]["htype"] != "group":
            continue
        # compare attributes
        for k in desc1[name]["attr"]:
            if k not in desc2[name]["attr"]:
                print("** Attribute '%s' only in '%s' (DIFF_UNIQ_ATTR_A)**" % (k, file1))
                differs = True
        for k in desc2[name]["attr"]:
            if k not in desc1[name]["attr"]:
                print("** Attribute '%s' only in '%s' (DIFF_UNIQ_ATTR_B)**" % (k, file2))
                differs = True
        # recurse into subgroup
        diff_groups(file1, grp1[name], file2, grp2[name], path+name+"/")

    # global attributes have not been checked yet
    if path == "/":
        desc1 = read_group(grp1)
        desc2 = read_group(grp2)

        # compare attributes
        for k in desc1["attr"]:
            if k not in desc2["attr"]:
                print("** Attribute '%s' only in '%s' (DIFF_UNIQ_ATTR_A)**" % (k, file1))
                differs = True
        for k in desc2["attr"]:
            if k not in desc1["attr"]:
                print("** Attribute '%s' only in '%s' (DIFF_UNIQ_ATTR_B)**" % (k, file2))
                differs = True
        for k in desc1["attr"]:
            if k in desc2["attr"]:
                v = desc1["attr"][k]
                v2 = desc2["attr"][k]
                if v != v2:
                    print("** Attribute '%s' has different type: '%s' and '%s' (DIFF_ATTR_DTYPE)" % (k, v, v2))
                    differs = True
                else:
                    result = compare_attributes(grp1, grp2, k)
                    if not result:
                        print("** Attribute '%s' value(s) different (DIFF_ATTR_VALUE)" % k)
                        differs = True

    return differs


def diff_files(file1, file2):
    print("Comparing '%s' and '%s'" % (file1, file2))
    try:
        f1 = h5py.File(file1, 'r')
    except IOError:
        print("Unable to open file '%s'" % file1)
        sys.exit(1)
    try:
        f2 = h5py.File(file2, 'r')
    except IOError:
        print("Unable to open file '%s'" % file2)
        sys.exit(1)
    return diff_groups(file1, f1["/"], file2, f2["/"], "/")

if __name__=="__main__":
    if len(sys.argv) != 3:
        print("Usage: %s <file1.h5> <file2.h5>" % sys.argv[0])
        sys.exit(2)

    if diff_files(sys.argv[1], sys.argv[2]):
        sys.exit(1)

    sys.exit(0)

# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

# <pep8-80 compliant>

"""Blender utils.
"""

import bpy
import mathutils

import rtcw_et_model_tools.mdi.mdi as mdi_m
import rtcw_et_model_tools.blender.core.fcurve as fcurve_m
import rtcw_et_model_tools.common.reporter as reporter_m


def from_ps_to_ws(mdi_object, blender_object, frame_start, frame_end):
    """Transform the data in an mdi object to world space by applying parent
    space transforms. The data in an mdi object is assumed to be given with
    all object space transforms already applied.
    """

    # TODO this could use some optimization
    # TODO scale on certain objects

    if isinstance(mdi_object, mdi_m.MDISurface):

        sample_vertex = mdi_object.vertices[0]
        if isinstance(sample_vertex, mdi_m.MDIMorphVertex):

            parent_object = blender_object.parent
            while parent_object:

                loc_pc, _, _ = blender_object.matrix_parent_inverse.decompose()

                locs_p, rots_p, scales_p = read_object_space_lrs(parent_object,
                                                                frame_start,
                                                                frame_end)

                for num_frame in range(len(locs_p)):

                    for mdi_morph_vertex in mdi_object.vertices:

                        location_c = mdi_morph_vertex.locations[num_frame]
                        normal_c = mdi_morph_vertex.normals[num_frame]
                        location_p = locs_p[num_frame]
                        rotation_p = rots_p[num_frame]
                        # scale_p = scales_p[num_frame]

                        location = location_p + \
                                   rotation_p @ (location_c + loc_pc)
                        normal = rotation_p @ normal_c

                        mdi_morph_vertex.locations[num_frame] = location
                        mdi_morph_vertex.normals[num_frame] = normal

                blender_object = parent_object
                parent_object = parent_object.parent

        elif isinstance(sample_vertex, mdi_m.MDIRiggedVertex):

            pass  # rigged vertices are given in armature space

        else:

            raise Exception("Found unkown type")

    elif isinstance(mdi_object, mdi_m.MDISkeleton):

        parent_object = blender_object.parent
        while parent_object:

            loc_pc, _, _ = blender_object.matrix_parent_inverse.decompose()

            locs_p, rots_p, scales_p = read_object_space_lrs(parent_object,
                                                             frame_start,
                                                             frame_end)

            for num_frame in range(len(locs_p)):

                for mdi_bone in mdi_object.bones:

                    location_c = mdi_bone.locations[num_frame]
                    orientation_c = mdi_bone.orientations[num_frame]

                    location_p = locs_p[num_frame]
                    rotation_p = rots_p[num_frame]
                    scale_p = scales_p[num_frame]

                    location = location_p + rotation_p @ (location_c + loc_pc)
                    orientation = rotation_p @ orientation_c

                    mdi_bone.locations[num_frame] = location
                    mdi_bone.orientations[num_frame] = orientation

            blender_object = parent_object
            parent_object = parent_object.parent

    elif isinstance(mdi_object, mdi_m.MDIFreeTag):

        parent_object = blender_object.parent
        while parent_object:

            loc_pc, _, _ = blender_object.matrix_parent_inverse.decompose()

            locs_p, rots_p, scales_p = read_object_space_lrs(parent_object,
                                                             frame_start,
                                                             frame_end)

            for num_frame in range(len(locs_p)):

                location_c = mdi_object.locations[num_frame]
                orientation_c = mdi_object.orientations[num_frame]

                location_p = locs_p[num_frame]
                rotation_p = rots_p[num_frame]
                scale_p = scales_p[num_frame]

                location = location_p + rotation_p @ (location_c + loc_pc)
                orientation = rotation_p @ orientation_c

                mdi_object.locations[num_frame] = location
                mdi_object.orientations[num_frame] = orientation

            blender_object = parent_object
            parent_object = parent_object.parent

    elif isinstance(mdi_object, mdi_m.MDIBoneTag):

        pass  # given in bone space

    elif isinstance(mdi_object, mdi_m.MDIBoneTagOff):

        pass  # # given in bone space

    else:

        raise Exception("Found unkown type")

def apply_parent_space_transforms(mdi_model, mesh_objects, armature_object,
                                  arrow_objects, frame_start = 0,
                                  frame_end = 0):

    for mesh_object in mesh_objects:

        mdi_surface = mdi_model.find_surface_by_name(mesh_object.name)
        if mdi_surface:
            from_ps_to_ws(mdi_surface, mesh_object, frame_start, frame_end)
        else:
            pass  # TODO

    if armature_object:
        from_ps_to_ws(mdi_model.skeleton,
                      armature_object,
                      frame_start,
                      frame_end)

    for arrow_object in arrow_objects:

        mdi_tag = mdi_model.find_tag_by_name(arrow_object.name)
        if mdi_tag:
            from_ps_to_ws(mdi_tag, arrow_object, frame_start, frame_end)
        else:
            pass  # TODO

def is_object_supported(mdi_object, blender_object):
    """Checks for constraints, modifiers and object space animation.
    """

    is_supported = True

    # TODO drivers

    # constraints not supported
    if len(blender_object.constraints) > 0:

        reporter_m.warning("Constraints for objects '{}' are generally not"
                            " supported"
                            .format(mdi_object.name))
        is_supported = False

    # TODO pose bones, edit bones?

    # modifiers
    # only for mesh objects supported
    if len(blender_object.modifiers) > 0:

        if isinstance(mdi_object, mdi_m.MDISurface):

            if len(blender_object.modifiers) == 1:

                try:
                    blender_object.modifiers['Armature']
                except:
                    reporter_m.warning("Only armature modifier allowed for"
                                       " this type of object '{}'"
                                   .format(mdi_object.name))
                    is_supported = False

            else:  # more than 1

                reporter_m.warning("Only armature modifier allowed for this"
                                   " type of object '{}'"
                                   .format(mdi_object.name))
                is_supported = False

        else:

            reporter_m.warning("Modifiers for this type of object '{}' are"
                               " generally not supported"
                                .format(mdi_object.name))
            is_supported = False

    else:

        pass  # ok

    # object space animation
    # not supported for rigged mesh objects and certain types of tags
    if isinstance(mdi_object, mdi_m.MDISurface):

        if mdi_object.vertices:

            sample_vertex = mdi_object.vertices[0]
            if isinstance(sample_vertex, mdi_m.MDIRiggedVertex):

                if blender_object.animation_data and \
                    blender_object.animation_data.action and \
                    blender_object.animation_data.action.fcurves:

                    fcurves = blender_object.animation_data.action.fcurves

                    fcurve_1 = fcurves.find(fcurve_m.DP_LOCATION)
                    fcurve_2 = fcurves.find(fcurve_m.DP_EULER)
                    fcurve_3 = fcurves.find(fcurve_m.DP_AXIS_ANGLE)
                    fcurve_4 = fcurves.find(fcurve_m.DP_QUATERNION)
                    fcurve_5 = fcurves.find(fcurve_m.DP_SCALE)

                    if fcurve_1 or fcurve_2 or fcurve_3 or fcurve_4 or \
                       fcurve_5:

                        reporter_m.warning("Object space animation of rigged"
                                           " mesh object '{}' not supported"
                                        .format(mdi_object.name))
                        is_supported = False

    elif isinstance(mdi_object, mdi_m.MDISkeleton):

        pass  # ok

    elif isinstance(mdi_object, mdi_m.MDIFreeTag):

        pass  # ok

    elif isinstance(mdi_object, mdi_m.MDIBoneTag) or \
         isinstance(mdi_object, mdi_m.MDIBoneTagOff):

        if blender_object.animation_data and \
           blender_object.animation_data.action and \
           blender_object.animation_data.action.fcurves:

            fcurves = blender_object.animation_data.action.fcurves

            fcurve_1 = fcurves.find(fcurve_m.DP_LOCATION)
            fcurve_2 = fcurves.find(fcurve_m.DP_EULER)
            fcurve_3 = fcurves.find(fcurve_m.DP_AXIS_ANGLE)
            fcurve_4 = fcurves.find(fcurve_m.DP_QUATERNION)
            fcurve_5 = fcurves.find(fcurve_m.DP_SCALE)

            if fcurve_1 or fcurve_2 or fcurve_3 or fcurve_4 or fcurve_5:

                reporter_m.warning("Arrow object '{}' object space animation"
                                   " not supported for arrow objects parented"
                                   " to a bone. They can only be animated by"
                                   " animating the bone"
                                   .format(mdi_object.name))
                is_supported = False

    return is_supported

def apply_object_transform(mdi_object, blender_object, frame_start, frame_end):
    """Applies the transforms given in object space including animation.
    """

    if isinstance(mdi_object, mdi_m.MDISurface):

        if mdi_object.vertices:

            # only for morph vertices
            sample_vertex = mdi_object.vertices[0]
            if isinstance(sample_vertex, mdi_m.MDIMorphVertex):

                locs, rots, scales = \
                    read_object_space_lrs(blender_object,
                                          frame_start,
                                          frame_end)

                for mdi_vertex in mdi_object.vertices:

                    for num_frame in range(len(locs)):

                        location_cs = mdi_vertex.locations[num_frame]
                        normal_cs = mdi_vertex.normals[num_frame]
                        loc_os = locs[num_frame]
                        rot_os = rots[num_frame]
                        scale_os = scales[num_frame]

                        # we can't do this inplace since some mdi_vertex objects
                        # might be duplicated during uv map pass, so just create
                        # a new vector
                        sx = location_cs[0] * scale_os[0]
                        sy = location_cs[1] * scale_os[1]
                        sz = location_cs[2] * scale_os[2]
                        location_scaled = mathutils.Vector((sx, sy, sz))

                        mdi_vertex.locations[num_frame] = \
                            loc_os + rot_os @ location_scaled

                        mdi_vertex.normals[num_frame] = rot_os @ normal_cs

            else:

                pass  # checked else where

    elif isinstance(mdi_object, mdi_m.MDISkeleton):

        locs, rots, scales = \
            read_object_space_lrs(blender_object,
                                  frame_start,
                                  frame_end)

        for mdi_bone in mdi_object.bones:

            for num_frame in range(len(locs)):

                location_cs = mdi_bone.locations[num_frame]
                orientation_cs = mdi_bone.orientations[num_frame]
                loc_os = locs[num_frame]
                rot_os = rots[num_frame]
                scale_os = scales[num_frame]

                mdi_bone.locations[num_frame] = loc_os + rot_os @ location_cs
                mdi_bone.orientations[num_frame] = rot_os @ orientation_cs

    elif isinstance(mdi_object, mdi_m.MDIFreeTag):

        pass  # already done

    elif isinstance(mdi_object, mdi_m.MDIBoneTag):

        pass  # TODO

    elif isinstance(mdi_object, mdi_m.MDIBoneTagOff):

        pass  # TODO

    else:

        raise Exception("Unknown object type during object transform")

def read_object_space_lrs(blender_object, frame_start = 0, frame_end = 0,
                          read_locs = True, read_rots = True,
                          read_scales = True):
    """Read object space location, rotation and scale values of an object. If
    not animated, return static values across frames. The returned values are
    assumed to be given without constraints, parents or modifiers applied.

    Args:

        blender_object
        frame_start
        frame_end
        read_locs
        read_rots
        read_scales

    Returns:

        (locations, rotations, scales)
    """

    # find out if its animated by searching for the fcurve of an action
    # TODO nla
    fcurves = None
    if blender_object.animation_data:

        action = blender_object.animation_data.action
        if action:

            fcurves = action.fcurves
            if not fcurves:

                reporter_m.warning("Action found with no fcurves on blender"
                                   " object '{}'"
                                   .format(blender_object.name))

        else:

            reporter_m.warning("Animation data with no action found on"
                               " blender object '{}'"
                               .format(blender_object.name))

    locations = []
    rotations = []
    scales = []
    if fcurves:

        # locations
        if read_locs:

            data_path = fcurve_m.DP_LOCATION
            locations = fcurve_m.read_locations(fcurves,
                                                data_path,
                                                frame_start,
                                                frame_end)

        # rotations
        if read_rots:

            rotation_mode = blender_object.rotation_mode

            if rotation_mode == 'XYZ' or rotation_mode == 'XZY' or \
               rotation_mode == 'YXZ' or rotation_mode == 'YZX' or \
               rotation_mode == 'ZXY' or rotation_mode == 'ZYX':

                data_path = fcurve_m.DP_EULER
                eulers = fcurve_m.read_eulers(fcurves,
                                              data_path,
                                              rotation_mode,
                                              frame_start,
                                              frame_end)

                if eulers:

                    for euler in eulers:

                        rotation = euler.to_matrix()
                        rotations.append(rotation)

            elif rotation_mode == 'AXIS_ANGLE':

                data_path = fcurve_m.DP_AXIS_ANGLE
                axis_angles = fcurve_m.read_axis_angles(fcurves,
                                                        data_path,
                                                        frame_start,
                                                        frame_end)

                if axis_angles:

                    for axis_angle in axis_angles:

                        rotation = axis_angle_to_matrix(axis_angle)
                        rotations.append(rotation)

            elif rotation_mode == 'QUATERNION':

                data_path = fcurve_m.DP_QUATERNION
                quaternions = fcurve_m.read_quaternions(fcurves,
                                                        data_path,
                                                        frame_start,
                                                        frame_end)

                if quaternions:

                    for quaternion in quaternions:

                        rotation = quaternion.to_matrix()
                        rotations.append(rotation)

            else:

                exception_string = "Unknown rotation mode found on blender" \
                                   " object '{}'".format(blender_object.name)
                raise Exception(exception_string)

        # scales
        if read_scales:

            data_path = fcurve_m.DP_SCALE
            scales = fcurve_m.read_scales(fcurves,
                                          data_path,
                                          frame_start,
                                          frame_end)

    if not locations and read_locs:

        loc, _, _ = blender_object.matrix_basis.decompose()
        locations = [loc] * (frame_end + 1 - frame_start)

    if not rotations and read_rots:

        _, rot, _ = blender_object.matrix_basis.decompose()
        rot = rot.to_matrix()
        rotations = [rot] * (frame_end + 1 - frame_start)

    if not scales and read_scales:

        _, _, scale = blender_object.matrix_basis.decompose()
        scales = [scale] * (frame_end + 1 - frame_start)

    return (locations, rotations, scales)

def write_object_space_lrs(blender_object, locations = None, rotations = None,
                           scales = None, frame_start = 0):
    """Write object space location, rotation and scale values of an object. The
    values are assumed to be given without constraints, parents or modifiers
    applied.

    Args:

        blender_object
        locations
        rotations
        scales
        frame_start
    """

    # ensure there is animation data to write to
    needs_animation_data = False
    if locations and len(locations) > 1:
            needs_animation_data = True
    if rotations and len(rotations) > 1:
            needs_animation_data = True
    if scales and len(scales) > 1:
            needs_animation_data = True

    if needs_animation_data:

        if not blender_object.animation_data:
            blender_object.animation_data_create()

        if not blender_object.animation_data.action:
            blender_object.animation_data.action = \
                bpy.data.actions.new(name=blender_object.name)

        # TODO check for fcurves?

    # locations
    if locations:

        num_frames = len(locations)
        if num_frames > 1:

            fcurves = blender_object.animation_data.action.fcurves
            data_path = fcurve_m.DP_LOCATION
            fcurve_m.write_locations(fcurves,
                                     data_path,
                                     locations,
                                     frame_start)

        elif num_frames == 1:

            blender_object.matrix_basis.translation = locations[0]

        else:

            pass  # nothing to write

    if rotations:

        num_frames = len(rotations)
        if num_frames > 1:

            fcurves = blender_object.animation_data.action.fcurves
            data_path = fcurve_m.DP_QUATERNION

            quaternions = []
            for rotation in rotations:

                quaternion = rotation.to_quaternion()
                quaternions.append(quaternion)

            fcurve_m.write_quaternions(fcurves,
                                       data_path,
                                       quaternions,
                                       frame_start)

        elif num_frames == 1:

            rotation_matrix = rotations[0]
            matrix_basis = blender_object.matrix_basis
            matrix_basis[0][0:3] = rotation_matrix[0][0:3]
            matrix_basis[1][0:3] = rotation_matrix[1][0:3]
            matrix_basis[2][0:3] = rotation_matrix[2][0:3]

        else:

            pass  # nothing to write

    if scales:

        num_frames = len(scales)
        if num_frames > 1:

            fcurves = blender_object.animation_data.action.fcurves
            data_path = fcurve_m.DP_SCALE
            fcurve_m.write_scales(fcurves, data_path, scales, frame_start)

        elif num_frames == 1:

            scale = scales[0]
            matrix_basis = blender_object.matrix_basis
            matrix_basis[0][0] = scale[0]
            matrix_basis[1][1] = scale[1]
            matrix_basis[2][2] = scale[2]

        else:

            pass  # nothing to write

    if needs_animation_data:

        fcurves = blender_object.animation_data.action.fcurves
        fcurve_m.set_interpolation_mode(fcurves, 'LINEAR')

def matrix_to_axis_angle(matrix):
    """TODO
    """

    axis_angle = None

    if True:
        raise Exception("Matrix to axis angle conversion not supported")

    return axis_angle

def axis_angle_to_matrix(axis_angle):
    """TODO
    """

    matrix = None

    if True:
        raise Exception("Axis angle to matrix conversion not supported")

    return matrix

# calculates a vector (x, y, z) orthogonal to v
def getOrthogonal(v):
    """TODO
    """

    x = 0
    y = 0
    z = 0

    if v[0] == 0: # x-axis is 0 => yz-plane

        x = 1
        y = 0
        z = 0

    else:

        if v[1] == 0: # y-axis is 0 => xz-plane

            x = 0
            y = 1
            z = 0

        else:

            if v[2] == 0: # z-axis is 0 => xy-plane

                x = 0
                y = 0
                z = 1

            else:

                # x*v0 + y*v1 + z*v2 = 0
                x = 1 / v[0]
                y = 1 / v[1]
                z = -((1/v[2]) * 2)

    return (x, y, z)

def draw_normals_in_frame(mdi_vertices, num_frame, collection,
                          mdi_skeleton = None):
    """TODO
    """

    for mdi_vertex in mdi_vertices:

        if isinstance(mdi_vertex, mdi_m.MDIMorphVertex):

            empty_object = bpy.data.objects.new("empty", None)
            empty_object.name = "vertex_normal"
            empty_object.empty_display_type = 'SINGLE_ARROW'
            empty_object.rotation_mode = 'QUATERNION'

            b3 = mdi_vertex.normals[num_frame]

            # find orthogonal basis vectors
            b2 = mathutils.Vector(getOrthogonal(b3))
            b1 = b2.cross(b3)

            # normalize
            b1.normalize()
            b2.normalize()
            b3.normalize()

            # build transformation matrix
            basis = mathutils.Matrix()
            basis[0].xyz = b1
            basis[1].xyz = b2
            basis[2].xyz = b3
            basis.transpose()
            basis.translation = mdi_vertex.locations[num_frame]

            empty_object.matrix_world = basis

            collection.objects.link(empty_object)

        elif isinstance(mdi_vertex, mdi_m.MDIRiggedVertex):

            empty_object = bpy.data.objects.new("empty", None)
            empty_object.name = "Normal"
            empty_object.empty_display_type = 'SINGLE_ARROW'
            empty_object.rotation_mode = 'QUATERNION'

            b3 = mdi_vertex.calc_normal_ms(mdi_skeleton, num_frame)

            # find orthogonal basis vectors
            b2 = mathutils.Vector(getOrthogonal(b3))
            b1 = b2.cross(b3)

            # normalize
            b1.normalize()
            b2.normalize()
            b3.normalize()

            # build transformation matrix
            basis = mathutils.Matrix()
            basis[0].xyz = b1
            basis[1].xyz = b2
            basis[2].xyz = b3
            basis.transpose()
            basis.translation = mdi_vertex.calc_location_ms(mdi_skeleton,
                                                            num_frame)

            empty_object.matrix_world = basis

            collection.objects.link(empty_object)

        else:

            pass  # TODO

def get_verts_from_bounds(min_bound, max_bound):
    """TODO
    """

    vertices = []

    v0 = (min_bound[0], min_bound[1], min_bound[2])
    v1 = (min_bound[0], max_bound[1], min_bound[2])
    v2 = (min_bound[0], min_bound[1], max_bound[2])
    v3 = (min_bound[0], max_bound[1], max_bound[2])

    v4 = (max_bound[0], max_bound[1], max_bound[2])
    v5 = (max_bound[0], min_bound[1], max_bound[2])
    v6 = (max_bound[0], max_bound[1], min_bound[2])
    v7 = (max_bound[0], min_bound[1], min_bound[2])

    vertices.append(v0)
    vertices.append(v1)
    vertices.append(v2)
    vertices.append(v3)
    vertices.append(v4)
    vertices.append(v5)
    vertices.append(v6)
    vertices.append(v7)

    return vertices

def draw_bounding_volume(mdi_bounding_volume):
    """TODO
    """

    min_bound = mdi_bounding_volume.aabbs[0].min_bound
    max_bound = mdi_bounding_volume.aabbs[0].max_bound

    vertices = get_verts_from_bounds(min_bound, max_bound)

    # faces
    faces = []

    f1 = (0, 1, 3, 2)
    f2 = (4, 5, 7, 6)

    f3 = (2, 3, 4, 5)
    f4 = (0, 1, 6, 7)

    f5 = (0, 2, 5, 7)
    f6 = (1, 3, 4, 6)

    faces.append(f1)
    faces.append(f2)
    faces.append(f3)
    faces.append(f4)
    faces.append(f5)
    faces.append(f6)

    name = "BoundingBox"
    mesh = bpy.data.meshes.new(name)
    mesh_object = bpy.data.objects.new(name, mesh)
    mesh_object.display_type = 'WIRE'

    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    mesh.validate(verbose=True)

    active_collection = \
        bpy.context.view_layer.active_layer_collection.collection
    active_collection.objects.link(mesh_object)

    num_frames = len(mdi_bounding_volume.aabbs)

    for num_frame in range(num_frames):

        shape_key = mesh_object.shape_key_add(name="Frame", from_mix=False)

        min_bound = mdi_bounding_volume.aabbs[num_frame].min_bound
        max_bound = mdi_bounding_volume.aabbs[num_frame].max_bound
        vertices = get_verts_from_bounds(min_bound, max_bound)

        for num_vertex, vertex in enumerate(vertices):

            x = vertex[0]
            y = vertex[1]
            z = vertex[2]
            shape_key.data[num_vertex].co = (x, y, z)

    mesh_object.data.shape_keys.use_relative = False

    for num_frame in range(num_frames):

        mesh_object.data.shape_keys.eval_time = 10.0 * num_frame
        mesh_object.data.shape_keys. \
            keyframe_insert('eval_time', frame = num_frame)

    mesh_object.data.update()

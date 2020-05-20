#ATS:test(SELF, label="Polyhedron clipping tests")

import unittest
from math import *
import time

from PolyClipper import *
from PolyClipperTestUtilities import *

# Create a global random number generator.
import random
rangen = random.Random()

#-------------------------------------------------------------------------------
# Make a cube                   |y     
#                               |      
#                               |____x 
#   3/-----/2                  /       
#   /     /|                  /z       
# 7|-----|6|
#  |     | |
#  |  0  | /1
#  |_____|/
#  4     5
#
cube_points = []
for coords in [(0,0,0),  (10,0,0),  (10,10,0),  (0,10,0),
               (0,0,10), (10,0,10), (10,10,10), (0,10,10)]:
    cube_points.append(Vector3d(*coords))

cube_neighbors = [[1, 4, 3],
                  [5, 0, 2],
                  [3, 6, 1],
                  [7, 2, 0],
                  [5, 7, 0],
                  [1, 6, 4],
                  [5, 2, 7],
                  [4, 6, 3]]

cube_facets = [[4, 5, 6, 7],
               [1, 2, 6, 5],
               [0, 3, 2, 1],
               [4, 7, 3, 0],
               [6, 2, 3, 7],
               [1, 5, 4, 0]]

#-------------------------------------------------------------------------------
# Make a non-convex notched thingy.                            |y     
#                                                              |      
#                                                              |____x 
#       6            5       3          2                     /       
#       /------------/      /----------/                     /z       
#      /            / \    /          /|
#     /            /   \ 4/          / |
#    /            /     \/          /  |
#    |------------\      /---------|9  |
#    |13        12 \    / 10       |   |
#    |              \  /           |   |
#    |               \/            |   |
#    |               11            |   |
#    |   0                         |  / 1
#    |                             | /
#    |------------------------------/
#    7                             8

notched_points = []
for coords in [(0,0,0), (4,0,0), (4,2,0), (3,2,0), (2,1,0), (1,2,0), (0,2,0),
               (0,0,1), (4,0,1), (4,2,1), (3,2,1), (2,1,1), (1,2,1), (0,2,1)]:
    notched_points.append(Vector3d(*coords))
notched_neighbors = [[7, 6, 1],   # 0
                     [0, 2, 8],   # 1
                     [1, 3, 9],   # 2
                     [4, 10, 2],  # 3
                     [5, 11, 3],  # 4
                     [6, 12, 4],  # 5
                     [13, 5, 0],  # 6
                     [8, 13, 0],  # 7
                     [1, 9, 7],   # 8
                     [2, 10, 8],  # 9
                     [9, 3, 11],  # 10
                     [10, 4, 12], # 11
                     [11, 5, 13], # 12
                     [7, 12, 6]]  # 13
notched_facets = [[6, 5, 4, 3, 2, 1, 0],
                  [7, 8, 9, 10, 11, 12, 13],
                  [1, 2, 9, 8],
                  [2, 3, 10, 9],
                  [3, 4, 11, 10],
                  [4, 5, 12, 11],
                  [5, 6, 13, 12],
                  [7, 13, 6, 0],
                  [0, 1, 8, 7]]

#-------------------------------------------------------------------------------
# A degenerate pyramid.  Just reuse the cube, but collapse one face.
degenerate_cube_points1 = []
for coords in [(0,0,0), (1,0,0), (1,1,0), (0,1,0),
               (0,0,1), (0,0,1), (0,0,1), (0,0,1)]:
    degenerate_cube_points1.append(Vector3d(*coords))

# Another one collapsing a different vertex.
degenerate_cube_points2 = []
for coords in [(0,0,0),  (10,0,0),  (10,10,0),  (10,10,0),
               (0,0,10), (10,0,10), (10,10,0), (10,10,0)]:
    degenerate_cube_points2.append(Vector3d(*coords))

#-------------------------------------------------------------------------------
# Compute the answer for zeroth and first moments
#-------------------------------------------------------------------------------
def moments_answer(poly):
    assert len(poly) >= 4
    origin = poly[0].position
    m0, m1 = 0.0, Vector3d(0, 0, 0)
    facets = extractFaces(poly)
    for facet in facets:
        n = len(facet)
        p0 = poly[facet[0]].position - origin
        for k in xrange(1,n-1):
            i = facet[k]
            j = facet[(k + 1) % n]
            p1 = poly[i].position - origin
            p2 = poly[j].position - origin
            dV = p0.dot(p1.cross(p2))
            m0 += dV                                    # 6x
            m1 += dV*(p0 + p1 + p2)                     # 24x
    m0 /= 6.0
    m1 /= 24.0*m0
    m1 += origin
    return m0, m1

#-------------------------------------------------------------------------------
# Find the maximum length across a polygon
#-------------------------------------------------------------------------------
def max_chord(poly):
    xmin = min([v.position.x for v in poly])
    xmax = max([v.position.x for v in poly])
    ymin = min([v.position.y for v in poly])
    ymax = max([v.position.y for v in poly])
    zmin = min([v.position.z for v in poly])
    zmax = max([v.position.z for v in poly])
    return (Vector3d(xmax, ymax, zmax) - Vector3d(xmin, ymin, zmin)).magnitude()

#-------------------------------------------------------------------------------
# Test harness
#-------------------------------------------------------------------------------
class TestPolyhedronClipping(unittest.TestCase):

    #---------------------------------------------------------------------------
    # setUp
    #---------------------------------------------------------------------------
    def setUp(self):
        self.convexPolyData = [(cube_points, cube_neighbors, cube_facets),
                               (degenerate_cube_points1, cube_neighbors, cube_facets),
                               (degenerate_cube_points2, cube_neighbors, cube_facets)]
        self.nonconvexPolyData = [(notched_points, notched_neighbors, notched_facets)]
        self.degeneratePolyData = [(degenerate_cube_points1, cube_neighbors, cube_facets),
                                   (degenerate_cube_points2, cube_neighbors, cube_facets)]
        self.polyData = self.convexPolyData + self.nonconvexPolyData
        self.ntests = 1000
        return

    #---------------------------------------------------------------------------
    # initializePolyhedron
    #---------------------------------------------------------------------------
    def test_initializePolyhedron(self):
        for points, neighbors, facets in self.polyData:
            poly = Polyhedron()
            initializePolyhedron(poly, points, neighbors)
            m0, m1 = moments(poly)
            M0, M1 = moments_answer(poly)
            self.failUnless(fuzzyEqual(m0, M0),
                            "Volume comparison failure: %g != %g" % (m0, M0))
            self.failUnless(fuzzyEqual((m1 - M1).magnitude(), 0.0),
                            "Centroid comparison failure: %s != %s" % (m1, M1))

    #---------------------------------------------------------------------------
    # collapseDegenerates
    #---------------------------------------------------------------------------
    def test_collapseDegenerates(self):
        for points, neighbors, facets in self.degeneratePolyData:
            poly0 = Polyhedron()
            initializePolyhedron(poly0, points, neighbors)
            assert len(poly0) == len(points)
            #writePolyOBJ(poly0, "poly0.obj")
            poly1 = Polyhedron(poly0)
            #writePolyOBJ(poly1, "poly1_initial.obj")
            collapseDegenerates(poly1, 1.0e-10)
            #writePolyOBJ(poly1, "poly1_collapse.obj")
            assert len(poly1) == 5
            vol0, centroid0 = moments(poly0)
            vol1, centroid1 = moments(poly1)
            #writePolyOBJ(poly1, "poly1_collapse.obj")
            self.failUnless(fuzzyEqual(vol1, vol0),
                            "Volume comparison failure: %g != %g" % (vol1, vol0))
            self.failUnless(fuzzyEqual((centroid1 - centroid0).magnitude(), 0.0),
                            "Centroid comparison failure: %s != %s" % (centroid1, centroid0))

    #---------------------------------------------------------------------------
    # Clip with planes passing through the polyhedron.
    #---------------------------------------------------------------------------
    def testClipInternalOnePlane(self):
        for points, neighbors, facets in self.polyData:
            poly = Polyhedron()
            initializePolyhedron(poly, points, neighbors)
            for i in xrange(self.ntests):
                planes1, planes2 = [], []
                p0 = Vector3d(rangen.uniform(0.0, 1.0),
                              rangen.uniform(0.0, 1.0),
                              rangen.uniform(0.0, 1.0))
                phat = Vector3d(rangen.uniform(-1.0, 1.0), 
                                rangen.uniform(-1.0, 1.0), 
                                rangen.uniform(-1.0, 1.0)).unitVector()
                planes1.append(Plane3d(p0,  phat))
                planes2.append(Plane3d(p0, -phat))
                chunk1 = Polyhedron(poly)
                chunk2 = Polyhedron(poly)
                clipPolyhedron(chunk1, planes1)
                clipPolyhedron(chunk2, planes2)
                v0, c0 = moments(poly)
                v1, c1 = moments(chunk1)
                v2, c2 = moments(chunk2)
                success = fuzzyEqual(v1 + v2, v0)
                if not success:
                    print "Failed on pass ", i
                    print "Plane: ", p0, phat
                    print "Poly:\n", list(poly)
                    print "Chunk 1:\n ", list(chunk1)
                    print "Chunk 2:\n ", list(chunk2)
                    print moments(chunk1)
                    print moments(chunk2)
                    print "Vol check: %g + %g = %g" % (v1, v2, v0)
                    writePolyOBJ(poly, "poly.obj")
                    writePolyOBJ(chunk1, "chunk1.obj")
                    writePolyOBJ(chunk2, "chunk2.obj")
                self.failUnless(success, "Plane clipping summing to wrong volumes: %s + %s = %s != %s" % (v1, v2, v1 + v2, v0))
        return

    # #---------------------------------------------------------------------------
    # # Clip with the same plane repeatedly.
    # #---------------------------------------------------------------------------
    # def testRedundantClip(self):
    #     for points, neighbors, facets in self.polyData:
    #         poly = Polyhedron(points, facets)
    #         PCpoly = Polyhedron()
    #         convertToPolyhedron(PCpoly, poly)
    #         for i in xrange(self.ntests):
    #             planes1, planes2 = [], []
    #             p0 = Vector3d(rangen.uniform(0.0, 1.0),
    #                         rangen.uniform(0.0, 1.0))
    #             phat = Vector3d(rangen.uniform(-1.0, 1.0), 
    #                           rangen.uniform(-1.0, 1.0)).unitVector()
    #             planes1.append(Plane3d(p0,  phat))
    #             planes2.append(Plane3d(p0,  phat))
    #             planes2.append(Plane3d(p0,  phat))
    #             PCchunk1 = Polyhedron(PCpoly)
    #             PCchunk2 = Polyhedron(PCpoly)
    #             clipPolyhedron(PCchunk1, planes1)
    #             clipPolyhedron(PCchunk2, planes2)
    #             chunk1 = Polyhedron()
    #             chunk2 = Polyhedron()
    #             convertFromPolyhedron(chunk1, PCchunk1)
    #             convertFromPolyhedron(chunk2, PCchunk2)
    #             success = fuzzyEqual(chunk1.volume, chunk2.volume)
    #             if not success:
    #                 print "Failed on pass ", i
    #                 print "Plane: ", p0, phat
    #                 print "Poly:\n", poly
    #                 print "Chunk 1:\n ", chunk1
    #                 print "Chunk 2:\n ", chunk2
    #                 vol1, cent1 = moments(PCchunk1)
    #                 vol2, cent2 = moments(PCchunk2)
    #                 print "Vol check: %g = %g" % (vol1, vol2)
    #                 writePolyhedronOBJ(poly, "poly.obj")
    #                 writePolyhedronOBJ(chunk1, "chunk_ONE.obj")
    #                 writePolyhedronOBJ(chunk2, "chunk_TWO.obj")
    #             self.failUnless(success,
    #                             "Redundant plane clipping wrong volumes: %s != %s" % (chunk1.volume,
    #                                                                                   chunk2.volume))
    #     return

    # #---------------------------------------------------------------------------
    # # Clip with planes passing outside the polyhedron -- null test.
    # #---------------------------------------------------------------------------
    # def testNullClipOnePlane(self):
    #     for points, neighbors, facets in self.polyData:
    #         poly = Polyhedron(points, facets)
    #         for i in xrange(self.ntests):
    #             r = rangen.uniform(2.0, 100.0) * (poly.xmax - poly.xmin).magnitude()
    #             theta = rangen.uniform(0.0, 2.0*pi)
    #             phat = Vector3d(cos(theta), sin(theta))
    #             p0 = poly.centroid + r*phat
    #             planes = []
    #             planes.append(Plane3d(p0, -phat))
    #             PCchunk = Polyhedron()
    #             convertToPolyhedron(PCchunk, poly)
    #             clipPolyhedron(PCchunk, planes)
    #             chunk = Polyhedron()
    #             convertFromPolyhedron(chunk, PCchunk)
    #             success = (chunk.volume == poly.volume)
    #             if not success:
    #                 writePolyhedronOBJ(poly, "poly.obj")
    #                 writePolyhedronOBJ(chunk, "chunk.obj")
    #             self.failUnless(success,
    #                             "Null plane clipping failure: %s != %s" % (chunk.volume, poly.volume))
    #     return

    # #---------------------------------------------------------------------------
    # # Clip with planes passing outside the polyhedron and rejecting the whole thing.
    # #---------------------------------------------------------------------------
    # def testFullClipOnePlane(self):
    #     for points, neighbors, facets in self.polyData:
    #         poly = Polyhedron(points, facets)
    #         for i in xrange(self.ntests):
    #             planes = []
    #             r = rangen.uniform(2.0, 100.0) * (poly.xmax - poly.xmin).magnitude()
    #             theta = rangen.uniform(0.0, 2.0*pi)
    #             phat = Vector3d(cos(theta), sin(theta))
    #             p0 = poly.centroid + r*phat
    #             planes.append(Plane3d(p0, phat))
    #             PCchunk = Polyhedron()
    #             convertToPolyhedron(PCchunk, poly)
    #             clipPolyhedron(PCchunk, planes)
    #             chunk = Polyhedron()
    #             convertFromPolyhedron(chunk, PCchunk)
    #             success = (chunk.volume == 0.0)
    #             if not success:
    #                 writePolyhedronOBJ(poly, "poly.obj")
    #                 writePolyhedronOBJ(chunk, "chunk.obj")
    #             self.failUnless(success,
    #                             "Full plane clipping failure: %s != %s" % (chunk.volume, poly.volume))
    #     return

    # #---------------------------------------------------------------------------
    # # Clip with planes passing through the polyhedron.
    # #---------------------------------------------------------------------------
    # def testClipInternalTwoPlanes(self):
    #     for points, neighbors, facets in self.polyData:
    #         poly = Polyhedron(points, facets)
    #         PCpoly = Polyhedron()
    #         convertToPolyhedron(PCpoly, poly)
    #         for i in xrange(self.ntests):
    #             p0 = Vector3d(rangen.uniform(0.0, 1.0),
    #                         rangen.uniform(0.0, 1.0),
    #                         rangen.uniform(0.0, 1.0))
    #             norm1 = Vector3d(rangen.uniform(-1.0, 1.0), 
    #                            rangen.uniform(-1.0, 1.0),
    #                            rangen.uniform(-1.0, 1.0)).unitVector3d()
    #             norm2 = Vector3d(rangen.uniform(-1.0, 1.0), 
    #                            rangen.uniform(-1.0, 1.0),
    #                            rangen.uniform(-1.0, 1.0)).unitVector3d()
    #             planes1 = []
    #             planes1.append(Plane3d(p0,  norm1))
    #             planes1.append(Plane3d(p0,  norm2))
    #             planes2 = []
    #             planes2.append(Plane3d(p0,  norm1))
    #             planes2.append(Plane3d(p0, -norm2))
    #             planes3 = []
    #             planes3.append(Plane3d(p0, -norm1))
    #             planes3.append(Plane3d(p0,  norm2))
    #             planes4 = []
    #             planes4.append(Plane3d(p0, -norm1))
    #             planes4.append(Plane3d(p0, -norm2))
    #             PCchunk1 = Polyhedron(PCpoly)
    #             PCchunk2 = Polyhedron(PCpoly)
    #             PCchunk3 = Polyhedron(PCpoly)
    #             PCchunk4 = Polyhedron(PCpoly)
    #             clipPolyhedron(PCchunk1, planes1)
    #             clipPolyhedron(PCchunk2, planes2)
    #             clipPolyhedron(PCchunk3, planes3)
    #             clipPolyhedron(PCchunk4, planes4)
    #             chunk1 = Polyhedron(poly)
    #             chunk2 = Polyhedron(poly)
    #             chunk3 = Polyhedron(poly)
    #             chunk4 = Polyhedron(poly)
    #             convertFromPolyhedron(chunk1, PCchunk1)
    #             convertFromPolyhedron(chunk2, PCchunk2)
    #             convertFromPolyhedron(chunk3, PCchunk3)
    #             convertFromPolyhedron(chunk4, PCchunk4)
    #             success = fuzzyEqual(chunk1.volume + chunk2.volume + chunk3.volume + chunk4.volume, poly.volume)
    #             if not success:
    #                 writePolyhedronOBJ(poly, "poly.obj")
    #                 writePolyhedronOBJ(chunk1, "chunk_1ONE_TWOPLANES.obj")
    #                 writePolyhedronOBJ(chunk2, "chunk_2TWO_TWOPLANES.obj")
    #                 writePolyhedronOBJ(chunk3, "chunk_3THREE_TWOPLANES.obj")
    #                 writePolyhedronOBJ(chunk4, "chunk_4FOUR_TWOPLANES.obj")
    #             self.failUnless(success,
    #                             "Two plane clipping summing to wrong volumes: %s + %s + %s + %s = %s != %s" % (chunk1.volume,
    #                                                                                                            chunk2.volume,
    #                                                                                                            chunk3.volume,
    #                                                                                                            chunk4.volume,
    #                                                                                                            chunk1.volume + chunk2.volume + chunk3.volume + chunk4.volume,
    #                                                                                                            poly.volume))
    #     return

    # #---------------------------------------------------------------------------
    # # Split a (convex) polyhedron into tetrahedra.
    # #---------------------------------------------------------------------------
    # def testSplitIntoTetrahedra(self):
    #     for points, neighbors, facets in self.convexPolyData:
    #         PCpoly = Polyhedron()
    #         initializePolyhedron(PCpoly, points, neighbors)
    #         tets = splitIntoTetrahedra(PCpoly)
    #         vol0, centroid0 = moments(PCpoly)
    #         volTets = 0.0
    #         centroidTets = Vector3d()
    #         for inds in tets:
    #             assert len(inds) == 4
    #             v0 = PCpoly[inds[0]].position
    #             v1 = PCpoly[inds[1]].position
    #             v2 = PCpoly[inds[2]].position
    #             v3 = PCpoly[inds[3]].position
    #             V = (v1 - v0).dot((v2 - v0).cross(v3 - v0))
    #             assert V >= 0.0
    #             volTets += V
    #             centroidTets += V*(v0 + v1 + v2 + v3)
    #         volTets /= 6.0
    #         centroidTets /= 24.0*volTets
    #         assert abs(volTets - vol0) < 1.0e-20
    #         assert (centroidTets - centroid0).magnitude() < 1.0e-20

if __name__ == "__main__":
    unittest.main()

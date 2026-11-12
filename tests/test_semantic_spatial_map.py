"""Reprojection, 3D stacking and fail-closed world-object targeting tests."""
import copy
import unittest

from betterinstincts.room_map_traverse import plan_semantic_3d_target
from betterinstincts.semantic_spatial_map import (
    SemanticSpatialError, calibrate_camera, compile_spatial_map,
    load_contract, plan_spatial_target,
)


def world_items():
    rows = [
        ("floor_anchor", "FLOOR", "FLOOR_1", (0, 0, 0), (1, 0.2, 1)),
        ("table", "TABLE", "FLOOR_1", (4, 1, 0), (2, 2, 2)),
        ("lamp", "LAMP", "FLOOR_1", (4, 2.5, 0), (0.5, 1, 0.5)),
        ("wall", "WALL", "FLOOR_1", (6, 2, 0), (0.3, 4, 6)),
        ("shelf", "WALL_SHELF", "FLOOR_1", (6, 2.5, 0), (0.4, 0.4, 1)),
        ("cabinet", "CABINET", "FLOOR_1", (1, 2, 0), (2, 4, 2)),
        ("item_inside", "SMALL_ITEM", "FLOOR_1", (1, 1, 0), (0.5, 0.5, 0.5)),
        ("side_chair", "CHAIR", "FLOOR_1", (2.2, 1, 0), (1, 2, 1)),
        ("upper", "LAMP", "FLOOR_2", (0, 6, 3), (1, 1, 1)),
        ("elevated_anchor", "LIGHT", "FLOOR_1", (1, 4, 2), (1, 1, 1)),
        ("deep_anchor", "LIGHT", "FLOOR_1", (3, 0, 5), (1, 1, 1)),
    ]
    return [{
        "object_id": name, "category": cat, "floor_id": floor,
        "world_center_xyz": list(center), "world_size_xyz": list(size),
        "pose_source": "EA_READ_ONLY", "pose_refs": ["fixture:ea"],
        "pose_build": "1.121.361.1020", "identity_source": "EA_CATALOG",
        "category_confidence": 1.0, "vertical_adjustable": name == "shelf",
    } for name, cat, floor, center, size in rows]


def link(child, parent, relation):
    return {"child_id": child, "parent_id": parent, "relation": relation,
            "evidence_source": "BUILD_INSPECT", "evidence_ref": "fixture:inspect"}


def spatial():
    return compile_spatial_map(lot_id="fixture-lot", game_build="1.121.361.1020",
                               observations=world_items(),
                               relations=[link("lamp", "table", "ON_TOP_OF"),
                                          link("shelf", "wall", "WALL_MOUNTED_TO"),
                                          link("item_inside", "cabinet", "INSIDE"),
                                          link("side_chair", "table", "BESIDE")])


def landmarks(world, *, camera="camera:fixed", outlier=False):
    # Synthetic noncoplanar 3D affine camera: x=2X+Y+Z+100, y=-X+3Y+2Z+50.
    names = ["floor_anchor", "table", "wall", "cabinet", "upper",
             "elevated_anchor", "deep_anchor"]
    result = []
    for i, oid in enumerate(names):
        x, y, z = world["objects"][oid]["center"]
        cx, cy = 2*x+y+z+100, -x+3*y+2*z+50
        if outlier and i == len(names) - 1:
            cx += 80
        result.append({"object_id": oid, "client_xy": [cx, cy],
                       "camera_revision": camera,
                       "capture_ref": "frame:A" if i % 2 == 0 else "frame:B",
                       "source": "HOST_OBSERVED"})
    return result


def current_world(world, cam, floor="FLOOR_1"):
    return {"lot_id": world["lot_id"], "game_build": world["game_build"],
            "floor_id": floor, "camera_revision": cam["camera_revision"],
            "capture_ref": cam["latest_capture_ref"], "source": "HOST_OBSERVED"}


class SemanticSpatialMapTests(unittest.TestCase):
    def test_execute_is_false_and_height_not_screen_y(self):
        self.assertFalse(load_contract()["execute_allowed_default"])
        model = spatial()
        self.assertFalse(model["execute_allowed"])
        self.assertEqual(model["objects"]["shelf"]["center"][1], 2.5)
        self.assertTrue(model["objects"]["shelf"]["vertical_adjustable"])
        self.assertEqual(len(model["relations"]), 4)

    def test_depth_cannot_be_guessed_from_2d_or_single_view(self):
        obs = world_items()
        obs[0]["pose_source"] = "NONE"
        with self.assertRaisesRegex(SemanticSpatialError, "UNSUPPORTED_3D_FROM_2D"):
            compile_spatial_map(lot_id="l", game_build="1.121.361.1020", observations=obs)
        obs = world_items()
        obs[0]["pose_source"] = "CALIBRATED_MULTIVIEW"
        obs[0]["pose_refs"] = ["one-capture"]
        with self.assertRaisesRegex(SemanticSpatialError, "MULTIVIEW"):
            compile_spatial_map(lot_id="l", game_build="1.121.361.1020", observations=obs)

    def test_calibration_recovers_elevation_and_fails_on_outlier(self):
        world = spatial()
        cam = calibrate_camera(world, camera_revision="camera:fixed",
                               landmarks=landmarks(world))
        self.assertLess(cam["rms_error_px"], 0.0001)
        self.assertFalse(cam["execute_allowed"])
        with self.assertRaisesRegex(SemanticSpatialError, "REPROJECTION_UNSTABLE"):
            calibrate_camera(world, camera_revision="camera:fixed",
                             landmarks=landmarks(world, outlier=True))
        loc = plan_spatial_target(world, cam, active_world=current_world(world, cam), object_id="shelf", requested_floor="FLOOR_1",
                                  camera_revision="camera:fixed", capture_ref=cam["latest_capture_ref"],
                                  visibility={"object_id": "shelf", "camera_revision": "camera:fixed",
                                              "capture_ref": cam["latest_capture_ref"], "visible": True,
                                              "target_identity_confirmed": True, "occluded": False,
                                              "bbox_client": [100, 40, 125, 95]})
        self.assertEqual(loc["state"], "FRAMING_CANDIDATE")
        self.assertAlmostEqual(loc["suggested_client_xy"][0], 114.5, places=3)
        self.assertIsNone(loc["click_permit"])
        self.assertFalse(loc["execute_allowed"])

    def test_obstructed_container_and_stale_camera_never_offer_pixels(self):
        world = spatial()
        cam = calibrate_camera(world, camera_revision="camera:fixed", landmarks=landmarks(world))
        args = dict(object_id="item_inside", requested_floor="FLOOR_1",
                    camera_revision="camera:fixed", capture_ref=cam["latest_capture_ref"],
                    visibility={"object_id": "item_inside", "capture_ref": cam["latest_capture_ref"],
                                "camera_revision": "camera:fixed", "visible": False,
                                "occluded": True})
        result = plan_spatial_target(world, cam, active_world=current_world(world, cam), **args)
        self.assertEqual(result["next_gate"], "OPEN_CONTAINER_THEN_REOBSERVE")
        self.assertIsNone(result["suggested_client_xy"])
        args["camera_revision"] = "camera:new-pan"
        self.assertEqual(plan_spatial_target(world, cam, active_world=current_world(world, cam), **args)["reason"], "STALE_OR_MISSING_CAMERA")

    def test_wrong_floor_unverified_identity_and_no_fresh_frame(self):
        world = spatial()
        cam = calibrate_camera(world, camera_revision="camera:fixed", landmarks=landmarks(world))
        args = dict(object_id="shelf", requested_floor="FLOOR_2",
                    camera_revision="camera:fixed", capture_ref=cam["latest_capture_ref"])
        self.assertEqual(plan_spatial_target(world, cam, active_world=current_world(world, cam), **args)["reason"], "FLOOR_NOT_ACTIVE")
        args["requested_floor"] = "FLOOR_1"
        args["capture_ref"] = "old-frame"
        self.assertEqual(plan_spatial_target(world, cam, active_world=current_world(world, cam), **args)["reason"], "STALE_CAPTURE")
        args["capture_ref"] = cam["latest_capture_ref"]
        args["visibility"] = {"object_id": "shelf", "capture_ref": cam["latest_capture_ref"],
                              "camera_revision": "camera:fixed", "visible": True,
                              "occluded": False, "target_identity_confirmed": False}
        self.assertEqual(plan_spatial_target(world, cam, active_world=current_world(world, cam), **args)["reason"], "TARGET_IDENTITY_AMBIGUOUS")

    def test_relationships_do_not_assume_every_floor_or_false_stack(self):
        with self.assertRaisesRegex(SemanticSpatialError, "CROSS_FLOOR"):
            compile_spatial_map(lot_id="lot", game_build="1.121.361.1020",
                                observations=world_items(), relations=[link("upper", "table", "ON_TOP_OF")])
        with self.assertRaisesRegex(SemanticSpatialError, "SUPPORT_GEOMETRY"):
            compile_spatial_map(lot_id="lot", game_build="1.121.361.1020",
                                observations=world_items(), relations=[link("shelf", "table", "ON_TOP_OF")])
        with self.assertRaisesRegex(SemanticSpatialError, "CONTAINMENT_GEOMETRY_CONFLICT"):
            compile_spatial_map(lot_id="lot", game_build="1.121.361.1020",
                                observations=world_items(), relations=[link("cabinet", "item_inside", "INSIDE")])
        duplicate_volume = copy.deepcopy(world_items()[-1])
        duplicate_volume["object_id"] = "same_volume"
        cycle_items = world_items() + [duplicate_volume]
        with self.assertRaisesRegex(SemanticSpatialError, "RELATION_CYCLE"):
            compile_spatial_map(lot_id="lot", game_build="1.121.361.1020",
                                observations=cycle_items,
                                relations=[link("deep_anchor", "same_volume", "INSIDE"),
                                           link("same_volume", "deep_anchor", "INSIDE")])

    def test_no_repeated_object_ids_unknown_class_or_build_guess(self):
        obs = world_items()
        with self.assertRaisesRegex(SemanticSpatialError, "DUPLICATE_OBJECT"):
            compile_spatial_map(lot_id="lot", game_build="1.121.361.1020", observations=obs+[copy.deepcopy(obs[0])])
        obs[0]["category_confidence"] = 0.5
        result = compile_spatial_map(lot_id="lot", game_build="1.121.361.1020", observations=obs)
        self.assertEqual(result["objects"]["floor_anchor"]["category"], "UNKNOWN_OBJECT")
        obs[1]["pose_build"] = "wrong-build"
        with self.assertRaisesRegex(SemanticSpatialError, "STALE_GAME_BUILD_POSE"):
            compile_spatial_map(lot_id="lot", game_build="1.121.361.1020", observations=obs)

    def test_camera_relocalization_is_bound_to_lot_build_and_geometry(self):
        world = spatial()
        cam = calibrate_camera(world, camera_revision="camera:fixed", landmarks=landmarks(world))
        common = dict(object_id="shelf", requested_floor="FLOOR_1",
                      camera_revision="camera:fixed", capture_ref=cam["latest_capture_ref"],
                      visibility={"object_id": "shelf", "camera_revision": "camera:fixed",
                                  "capture_ref": cam["latest_capture_ref"], "visible": True,
                                  "target_identity_confirmed": True, "occluded": False,
                                  "bbox_client": [100, 40, 125, 95]})
        for field, value in [("lot_id", "different-lot"),
                             ("game_build", "different-build")]:
            wrong = copy.deepcopy(world)
            wrong[field] = value
            with self.subTest(field=field):
                self.assertEqual(plan_spatial_target(wrong, cam, active_world=current_world(wrong, cam), **common)["reason"],
                                 "STALE_OBJECT_MAP")
        rearranged = copy.deepcopy(world)
        rearranged["objects"]["shelf"]["center"] = (6, 3.5, 0)
        self.assertEqual(plan_spatial_target(rearranged, cam, active_world=current_world(rearranged, cam), **common)["reason"],
                         "STALE_OBJECT_MAP")


    def test_stale_map_and_stale_camera_cannot_cross_active_world(self):
        world = spatial()
        cam = calibrate_camera(world, camera_revision="camera:fixed", landmarks=landmarks(world))
        common = dict(object_id="shelf", requested_floor="FLOOR_1",
                      camera_revision="camera:fixed", capture_ref=cam["latest_capture_ref"])
        self.assertEqual(plan_spatial_target(world, cam, **common)["reason"], "ACTIVE_WORLD_UNVERIFIED")
        attested = current_world(world, cam)
        scenarios = [({"lot_id": "other-lot"}, "ACTIVE_WORLD_MISMATCH"),
                     ({"game_build": "other-build"}, "ACTIVE_WORLD_MISMATCH"),
                     ({"floor_id": "FLOOR_2"}, "ACTIVE_FLOOR_MISMATCH"),
                     ({"capture_ref": "old"}, "ACTIVE_WORLD_STALE"),
                     ({"source": "AGENT_GUESS"}, "ACTIVE_WORLD_UNVERIFIED")]
        for delta, expected in scenarios:
            with self.subTest(delta=delta):
                result = plan_spatial_target(world, cam, active_world={**attested, **delta}, **common)
                self.assertEqual(result["reason"], expected)
                self.assertIsNone(result["suggested_client_xy"])

    def test_semantic_unknown_and_room_bridge_cannot_grant_action(self):
        world = spatial()
        cam = calibrate_camera(world, camera_revision="camera:fixed", landmarks=landmarks(world))
        active = current_world(world, cam)
        visibility = {"object_id": "shelf", "camera_revision": "camera:fixed",
                      "capture_ref": cam["latest_capture_ref"], "visible": True,
                      "target_identity_confirmed": True, "occluded": False,
                      "bbox_client": [100, 40, 125, 95]}
        common = dict(spatial_map=world, camera_calibration=cam, object_id="shelf",
                      active_floor_id="FLOOR_1", camera_revision="camera:fixed",
                      capture_ref=cam["latest_capture_ref"], visibility=visibility)
        self.assertEqual(plan_semantic_3d_target(**common)["reason"], "ACTIVE_WORLD_UNVERIFIED")
        self.assertEqual(plan_semantic_3d_target(**common, active_world=active)["state"], "FRAMING_CANDIDATE")
        unknown = copy.deepcopy(world)
        unknown["objects"]["shelf"]["category"] = "UNKNOWN_OBJECT"
        recalibrated = calibrate_camera(unknown, camera_revision="camera:fixed",
                                        landmarks=landmarks(unknown))
        result = plan_spatial_target(unknown, recalibrated, active_world=active,
                                     object_id="shelf", requested_floor="FLOOR_1",
                                     camera_revision="camera:fixed",
                                     capture_ref=cam["latest_capture_ref"], visibility=visibility)
        self.assertEqual(result["reason"], "TARGET_CATEGORY_UNVERIFIED")
        self.assertFalse(result["execute_allowed"])
        self.assertIsNone(result["click_permit"])

    def test_camera_collinearity_cannot_fake_height_estimate(self):
        world = spatial()
        lm = landmarks(world)
        for mark in lm:
            # Repeated map location but unique ID cannot establish rank.
            world["objects"][mark["object_id"]]["center"] = (0, 0, 0)
        with self.assertRaisesRegex(SemanticSpatialError, "CAMERA_LANDMARKS_DEGENERATE"):
            calibrate_camera(world, camera_revision="camera:fixed", landmarks=lm)

    def test_camera_requires_two_frame_identities(self):
        world = spatial()
        lm = landmarks(world)
        for mark in lm:
            mark["capture_ref"] = "one"
        with self.assertRaisesRegex(SemanticSpatialError, "LANDMARKS_REQUIRE_DISTINCT_FRAMES"):
            calibrate_camera(world, camera_revision="camera:fixed", landmarks=lm)


if __name__ == "__main__":
    unittest.main()

import copy
import json
import math
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from gait.core import plan, validate, trajectory, measure, solve_leg, sample, limbs, SCHEMA
ROOT=Path(__file__).resolve().parents[1]

class GaitTests(unittest.TestCase):
    def test_three_examples(self):
        for path in (ROOT/'examples/gait').glob('*.json'):
            if '.rig.' in path.name:continue
            c=validate(json.loads(path.read_text()))
            self.assertTrue(measure(c,trajectory(c))['passed'],path.name)
    def test_speed_identities(self):
        for kind in ('biped','quadruped'):
            for speed in (.02,.35,.65,1.):
                c=plan(kind=kind,speed_mps=speed)
                self.assertAlmostEqual(c['stride_m'],c['cycle_s']*speed)
                self.assertAlmostEqual(c['cycle_s']*c['cadence_steps_per_s'],2)
                self.assertEqual(round(c['cycle_s']*c['fps']),c['cycle_s']*c['fps'])
    def test_age_and_state(self):
        normal=plan();elder=plan(age_years=75);tired=plan(state='tired')
        self.assertLess(elder['step_length_m'],normal['step_length_m'])
        self.assertLess(tired['foot_clearance_m'],normal['foot_clearance_m'])
        self.assertGreater(tired['stance_fraction'],normal['stance_fraction'])
    def test_proportions(self):
        self.assertGreater(plan(leg_length_m=1.2)['stride_m'],plan(leg_length_m=.6)['stride_m'])
    def test_slip_detection(self):
        c=plan();rows=trajectory(c);rows[1]['feet']['left']['position'][0]+=.05
        self.assertFalse(measure(c,rows)['passed'])
    def test_accumulated_contact_drift(self):
        c=plan();rows=trajectory(c)
        for i,row in enumerate(rows):
            if row['feet']['left']['stance']:row['feet']['left']['position'][0] += i*.0001
        self.assertFalse(measure(c,rows)['passed'])
    def test_stance_duration_consistency(self):
        c=plan();c['stance_duration_s'] += .1
        with self.assertRaises(ValueError):validate(c)
    def test_fractional_frame_cycle_rejected(self):
        c=plan();c['fps']=31
        with self.assertRaises(ValueError):validate(c)
    def test_penetration_detection(self):
        c=plan();rows=trajectory(c);rows[10]['feet']['right']['position'][2]=-.1
        self.assertFalse(measure(c,rows)['passed'])
    def test_position_seam_detection(self):
        c=plan();rows=trajectory(c);rows[-1]['feet']['right']['position'][0]+=.1
        self.assertFalse(measure(c,rows)['passed'])
    def test_velocity_seam_detection(self):
        c=plan();rows=trajectory(c);rows[-2]['feet']['right']['position'][2]+=.05
        self.assertFalse(measure(c,rows)['passed'])
    def test_unknown_fields(self):
        c=plan();c['hallucinated_gpt_field']=4
        with self.assertRaises(ValueError):validate(c)
    def test_nonfinite(self):
        for value in (float('nan'),float('inf'),-1):
            with self.assertRaises(ValueError):plan(speed_mps=value)
    def test_invalid_phase(self):
        c=plan();c['phase_offsets']['front_left']=.3
        with self.assertRaises(ValueError):validate(c)
    def test_snake_reserved(self):
        c=plan();c['type']='serpentine'
        with self.assertRaises(NotImplementedError):validate(c)
    def test_contradictory_gpt_data(self):
        c=plan();c['cadence_steps_per_s']=1
        with self.assertRaises(ValueError):validate(c)
    def test_boolean_number(self):
        c=plan();c['fps']=True
        with self.assertRaises(ValueError):validate(c)
    def test_running_rejected(self):
        with self.assertRaises(ValueError):plan(speed_mps=10)
    def test_ik_lengths(self):
        knee,angles=solve_leg([.02,0,.8],[0,.1,0],.45,.45)
        self.assertAlmostEqual(math.dist(knee,[.02,0,.8]),.45)
        self.assertAlmostEqual(math.dist(knee,[0,.1,0]),.45)
        self.assertGreater(angles['knee'],0)
    def test_unreachable(self):
        with self.assertRaises(ValueError):solve_leg([0,0,2],[0,0,0],.4,.4)
    def test_schema_draft202012(self):
        try:import jsonschema
        except ImportError:self.skipTest('optional jsonschema not installed')
        schema=json.loads(SCHEMA.read_text());jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator.check_schema(json.loads((ROOT/'schemas/gait-animation.schema.json').read_text()))
        for path in (ROOT/'examples/gait').glob('*.json'):
            if '.rig.' not in path.name:jsonschema.validate(json.loads(path.read_text()),schema)
    def test_all_example_legs_reachable(self):
        for path in (ROOT/'examples/gait').glob('*.json'):
            if '.rig.' in path.name:continue
            c=json.loads(path.read_text());length=c['body']['leg_length_m'];ratio=c['body']['upper_leg_ratio']
            for row in trajectory(c):
                for n,foot in row['feet'].items():
                    base_y=c['body']['body_length_m']/2*(1 if n.startswith('front') else -1) if c['type']=='quadruped' else 0
                    hip=[(-1 if n.endswith('left') else 1)*c['body']['hip_width_m']/2+row['com'][0],row['root'][1]+base_y+row['com'][1],length*.88+row['com'][2]]
                    _,angles=solve_leg(hip,foot['position'],length*ratio,length*(1-ratio),-1 if n.startswith('front') else 1)
                    for joint,a in angles.items():self.assertTrue(c['joint_limits_rad'][joint][0]<=a<=c['joint_limits_rad'][joint][1])

if __name__=='__main__':unittest.main()

import copy
import unittest
import ci_evidence

SHA='a'*40
def fixtures():
    expected={'repository':'owner/repo','head_repository':'owner/repo','head_sha':SHA,'run_id':42,'workflow_id':9,'attempt':2,
              'jobs':[{'name':'preflight','steps':['Replay']} ]}
    run={'id':42,'workflow_id':9,'run_attempt':2,'head_sha':SHA,'event':'pull_request','status':'completed','conclusion':'success',
         'repository':{'full_name':'owner/repo'},'head_repository':{'full_name':'owner/repo'}}
    job={'id':7,'run_id':42,'run_attempt':2,'name':'preflight','status':'completed','conclusion':'success',
         'steps':[{'name':'Replay','status':'completed','conclusion':'success'}]}
    return expected,run,{'total_count':1,'jobs':[job]}

class EvidenceTests(unittest.TestCase):
    def evaluate(self,mutate=None):
        expected,run,jobs=fixtures()
        if mutate:mutate(expected,run,jobs)
        return ci_evidence.evaluate(run,jobs,expected)
    def test_consistent_is_explicitly_not_proof_of_source_or_checkout(self):
        r=self.evaluate();self.assertEqual(r['state'],'consistent');self.assertFalse(r['source_authenticated']);self.assertFalse(r['actual_checkout_verified']);self.assertFalse(r['agent_execution_verified'])
    def test_stale_commit_rejected(self):
        self.assertEqual(self.evaluate(lambda e,r,j:r.update(head_sha='b'*40))['state'],'conflict')
    def test_wrong_repository_rejected(self):
        self.assertEqual(self.evaluate(lambda e,r,j:r['head_repository'].update(full_name='fork/repo'))['state'],'conflict')
    def test_wrong_run_or_attempt_rejected(self):
        for field,value in [('run_id',43),('run_attempt',1)]:
            with self.subTest(field=field):self.assertEqual(self.evaluate(lambda e,r,j:j['jobs'][0].update({field:value}))['state'],'conflict')
    def test_successful_run_with_skipped_required_step_fails(self):
        self.assertEqual(self.evaluate(lambda e,r,j:j['jobs'][0]['steps'][0].update(conclusion='skipped'))['state'],'failed')
    def test_failed_required_job_fails(self):
        self.assertEqual(self.evaluate(lambda e,r,j:j['jobs'][0].update(conclusion='failure'))['state'],'failed')
    def test_pending_not_called_success(self):
        self.assertEqual(self.evaluate(lambda e,r,j:r.update(status='in_progress',conclusion=None))['state'],'pending')
    def test_missing_required_job_inconclusive(self):
        self.assertEqual(self.evaluate(lambda e,r,j:j.update(total_count=0,jobs=[]))['state'],'inconclusive')
    def test_truncated_page_inconclusive(self):
        self.assertEqual(self.evaluate(lambda e,r,j:j.update(total_count=2))['state'],'inconclusive')
    def test_duplicate_job_name_inconclusive(self):
        def change(e,r,j):
            j['jobs'].append(copy.deepcopy(j['jobs'][0]));j['jobs'][1]['id']=8;j['total_count']=2
        self.assertEqual(self.evaluate(change)['state'],'inconclusive')
    def test_duplicate_required_step_inconclusive(self):
        self.assertEqual(self.evaluate(lambda e,r,j:j['jobs'][0]['steps'].append(copy.deepcopy(j['jobs'][0]['steps'][0])))['state'],'inconclusive')
    def test_missing_expected_identity_is_invalid(self):
        self.assertEqual(self.evaluate(lambda e,r,j:e.pop('head_sha'))['state'],'invalid_input')
    def test_boolean_id_is_not_integer(self):
        self.assertEqual(self.evaluate(lambda e,r,j:e.update(run_id=True))['state'],'invalid_input')

if __name__=='__main__':unittest.main()

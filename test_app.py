import unittest
import app

class PrototypeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if app.os.getenv('DB2_CONNECTION_STRING'):
            raise RuntimeError('Unset DB2_CONNECTION_STRING before running local tests.')
        app.init_demo()
        cls.client=app.app.test_client()

    def test_dashboard(self):
        response=self.client.get('/')
        self.assertEqual(response.status_code,200)
        self.assertIn(b'Demand surge simulator',response.data)

    def test_surge_is_read_only_and_changes_coverage(self):
        baseline=self.client.get('/api/overview').get_json()
        card=next(c for c in baseline['cards'] if c['daily_demand'] > 0)
        response=self.client.post('/api/scenario',json={'hospital_id':card['hospital_id'],'medicine_id':card['medicine_id'],'demand_multiplier':2})
        self.assertEqual(response.status_code,200)
        result=response.get_json()
        self.assertLess(result['after']['days_left'],result['before']['days_left'])
        self.assertEqual(baseline,self.client.get('/api/overview').get_json())

    def test_invalid_scenario_rejected(self):
        for value in [-1, 4, '2', None]:
            response=self.client.post('/api/scenario',json={'hospital_id':1,'medicine_id':1,'demand_multiplier':value})
            self.assertEqual(response.status_code,400)

    def test_donor_reserve(self):
        data=self.client.get('/api/overview').get_json()
        for card in data['cards']:
            allocated=sum(r['quantity'] for r in data['recommendations'] if r['source']==card['hospital'] and r['medicine']==card['medicine'])
            if allocated: self.assertGreaterEqual(card['quantity']-allocated+1.5, 30*card['daily_demand'])

if __name__=='__main__': unittest.main()

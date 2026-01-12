/*
Copyright 2017 OpFocus, Inc

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation 
files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, 
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the 
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES 
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE 
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR 
IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.		
*/
@isTest
public class LightningLookupControllerTest {

	/**
	 * Helper method to get an Account RecordTypeId
	 * The validation rule requires a RecordTypeId to be set
	 */
	private static Id getAccountRecordTypeId() {
		// Try to find 'Business' RecordType first (common in Shulman orgs)
		List<RecordType> recordTypes = [
			SELECT Id
			FROM RecordType
			WHERE SObjectType = 'Account'
			AND DeveloperName = 'Business'
			LIMIT 1
		];
		
		if (!recordTypes.isEmpty()) {
			return recordTypes[0].Id;
		}
		
		// Fallback to any Account RecordType
		recordTypes = [
			SELECT Id
			FROM RecordType
			WHERE SObjectType = 'Account'
			LIMIT 1
		];
		
		if (!recordTypes.isEmpty()) {
			return recordTypes[0].Id;
		}
		
		// If no RecordType exists, return null (will fail validation, but that's expected)
		return null;
	}

	static testMethod void myTest1() {
		// Create Account with RecordTypeId to satisfy validation rule
		// Name must be in "FirstName LastName" format to satisfy validation rule requiring "last name"
		// Use SObject.put() for dynamic field access to avoid compile errors when fields aren't available
		Account acct = new Account(
			Name = 'Test Company'
		);
		Id recordTypeId = getAccountRecordTypeId();
		if (recordTypeId != null) {
			try {
				acct.put('RecordTypeId', recordTypeId);
			} catch (Exception e) {
				// RecordTypeId may not be available - ignore and continue
			}
		}
		try {
			acct.put('litify_pm__Last_Name__c', 'Test');
		} catch (Exception e) {
			// litify_pm__Last_Name__c may not be available - ignore and continue
		}
		System.debug('DEBUG: Creating Account with Name = ' + acct.Name);
		insert acct;
		// Re-query to get the actual Name value set by automation/triggers
		acct = [SELECT Id, Name FROM Account WHERE Id = :acct.Id];
		System.debug('DEBUG: After insert, acct.Name = ' + acct.Name);
		LightningLookupController.LookupRecords res = LightningLookupController.getRecords('Account', '', 'Name', '', 'Name like \'test%\'','','');
		System.assertEquals(null,res);
		res = LightningLookupController.getRecords('Account', 'Id', '', '', 'Name like \'test%\'','','');
		System.assertEquals(null,res);
		res = LightningLookupController.getRecords('Account', 'Id', '', 'CreatedDate', 'Name like \'test%\'','','');
		System.assertEquals(null,res);
		res = LightningLookupController.getRecords('Account', '', '', 'CreatedDate', 'Name like \'test%\'','','');
		System.assertEquals(null,res);
		res = LightningLookupController.getRecords('Account', 'Id', 'Name', 'CreatedDate', 'Name like \'test%\'','','');
		System.assertEquals(1,res.lstDisplay.size());
		System.assertEquals(1,res.lstValue.size());
		System.assertEquals(1,res.lstRecords.size());
		res = LightningLookupController.getRecords('Account', 'Id', 'Name', 'CreatedDate', 'Name like \'hufdehf%\'','','');
		System.assertEquals(1,res.lstDisplay.size());
		System.assertEquals(1,res.lstValue.size());
		System.assertEquals(1,res.lstRecords.size());
		System.assertEquals('No records found!',res.lstDisplay[0]);
		String s = LightningLookupController.getHelpText('Account.Name');
		s = LightningLookupController.getReference('Account.OwnerId');
		System.assertEquals('User',s);
		res = LightningLookupController.getFieldValue('Account', acct.Id, 'Name');
                System.debug('DEBUG: acct.Name = ' + acct.Name);
                System.debug('DEBUG: res.lstDisplay[0] = ' + res.lstDisplay[0]);
		System.assertEquals(acct.Name,res.lstDisplay[0]);
		System.assertEquals(acct.Id,res.lstValue[0]);
		System.assertEquals(1, res.lstRecords.size());
	}
	
}

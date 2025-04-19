
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/components/ui/use-toast';
import { MultiStepForm } from './MultiStepForm';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Textarea } from '@/components/ui/textarea';
import { Checkbox } from '@/components/ui/checkbox';

// Personal Information Step
function PersonalInfoStep({ formData, updateFormData }: any) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="lastName">Last Name (Family Name)</Label>
          <Input 
            id="lastName"
            value={formData.lastName || ''}
            onChange={(e) => updateFormData({ lastName: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="firstName">First Name (Given Name)</Label>
          <Input 
            id="firstName"
            value={formData.firstName || ''}
            onChange={(e) => updateFormData({ firstName: e.target.value })}
          />
        </div>
      </div>
      
      <div>
        <Label htmlFor="birthDate">Date of Birth</Label>
        <Input 
          id="birthDate"
          type="date"
          value={formData.birthDate || ''}
          onChange={(e) => updateFormData({ birthDate: e.target.value })}
        />
      </div>
      
      <div>
        <Label htmlFor="birthPlace">Place of Birth (City, Country)</Label>
        <Input 
          id="birthPlace"
          value={formData.birthPlace || ''}
          onChange={(e) => updateFormData({ birthPlace: e.target.value })}
        />
      </div>
      
      <div>
        <Label htmlFor="nationality">Nationality</Label>
        <Input 
          id="nationality"
          value={formData.nationality || ''}
          onChange={(e) => updateFormData({ nationality: e.target.value })}
        />
      </div>
    </div>
  );
}

// Address and Contact Step
function ContactInfoStep({ formData, updateFormData }: any) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="streetAddress">Street Address</Label>
        <Input 
          id="streetAddress"
          value={formData.streetAddress || ''}
          onChange={(e) => updateFormData({ streetAddress: e.target.value })}
        />
      </div>
      
      <div className="grid grid-cols-3 gap-4">
        <div>
          <Label htmlFor="city">City</Label>
          <Input 
            id="city"
            value={formData.city || ''}
            onChange={(e) => updateFormData({ city: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="state">State/Province</Label>
          <Input 
            id="state"
            value={formData.state || ''}
            onChange={(e) => updateFormData({ state: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="postalCode">Postal Code</Label>
          <Input 
            id="postalCode"
            value={formData.postalCode || ''}
            onChange={(e) => updateFormData({ postalCode: e.target.value })}
          />
        </div>
      </div>
      
      <div>
        <Label htmlFor="country">Country</Label>
        <Input 
          id="country"
          value={formData.country || ''}
          onChange={(e) => updateFormData({ country: e.target.value })}
        />
      </div>
      
      <div>
        <Label htmlFor="phone">Phone Number</Label>
        <Input 
          id="phone"
          value={formData.phone || ''}
          onChange={(e) => updateFormData({ phone: e.target.value })}
        />
      </div>
      
      <div>
        <Label htmlFor="email">Email Address</Label>
        <Input 
          id="email"
          type="email"
          value={formData.email || ''}
          onChange={(e) => updateFormData({ email: e.target.value })}
        />
      </div>
    </div>
  );
}

// Passport Information Step
function PassportInfoStep({ formData, updateFormData }: any) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="passportNumber">Passport Number</Label>
        <Input 
          id="passportNumber"
          value={formData.passportNumber || ''}
          onChange={(e) => updateFormData({ passportNumber: e.target.value })}
        />
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="passportIssueDate">Issue Date</Label>
          <Input 
            id="passportIssueDate"
            type="date"
            value={formData.passportIssueDate || ''}
            onChange={(e) => updateFormData({ passportIssueDate: e.target.value })}
          />
        </div>
        <div>
          <Label htmlFor="passportExpiryDate">Expiry Date</Label>
          <Input 
            id="passportExpiryDate"
            type="date"
            value={formData.passportExpiryDate || ''}
            onChange={(e) => updateFormData({ passportExpiryDate: e.target.value })}
          />
        </div>
      </div>
      
      <div>
        <Label htmlFor="passportIssuingAuthority">Issuing Authority</Label>
        <Input 
          id="passportIssuingAuthority"
          value={formData.passportIssuingAuthority || ''}
          onChange={(e) => updateFormData({ passportIssuingAuthority: e.target.value })}
        />
      </div>
    </div>
  );
}

// Travel Information Step
function TravelInfoStep({ formData, updateFormData }: any) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="purposeOfTrip">Purpose of Trip</Label>
        <RadioGroup 
          value={formData.purposeOfTrip || ""}
          onValueChange={(value) => updateFormData({ purposeOfTrip: value })}
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="business" id="business" />
            <Label htmlFor="business">Business/Conference</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="tourism" id="tourism" />
            <Label htmlFor="tourism">Tourism/Vacation</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="education" id="education" />
            <Label htmlFor="education">Education/Study</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="medical" id="medical" />
            <Label htmlFor="medical">Medical Treatment</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="other" id="other" />
            <Label htmlFor="other">Other</Label>
          </div>
        </RadioGroup>
      </div>
      
      {formData.purposeOfTrip === 'other' && (
        <div>
          <Label htmlFor="purposeOfTripOther">Please Specify</Label>
          <Input 
            id="purposeOfTripOther"
            value={formData.purposeOfTripOther || ''}
            onChange={(e) => updateFormData({ purposeOfTripOther: e.target.value })}
          />
        </div>
      )}
      
      <div>
        <Label htmlFor="intendedArrivalDate">Intended Date of Arrival</Label>
        <Input 
          id="intendedArrivalDate"
          type="date"
          value={formData.intendedArrivalDate || ''}
          onChange={(e) => updateFormData({ intendedArrivalDate: e.target.value })}
        />
      </div>
      
      <div>
        <Label htmlFor="intendedLengthOfStay">Intended Length of Stay</Label>
        <Input 
          id="intendedLengthOfStay"
          placeholder="e.g., 14 days, 3 months"
          value={formData.intendedLengthOfStay || ''}
          onChange={(e) => updateFormData({ intendedLengthOfStay: e.target.value })}
        />
      </div>
      
      <div>
        <Label>Have you previously visited the United States?</Label>
        <RadioGroup 
          value={formData.previouslyVisitedUS || ""}
          onValueChange={(value) => updateFormData({ previouslyVisitedUS: value })}
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="yes" id="previousVisitYes" />
            <Label htmlFor="previousVisitYes">Yes</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="no" id="previousVisitNo" />
            <Label htmlFor="previousVisitNo">No</Label>
          </div>
        </RadioGroup>
      </div>
    </div>
  );
}

// Previous Visa Step - Conditional based on previous US visit
function PreviousVisaStep({ formData, updateFormData }: any) {
  return (
    <div className="space-y-4">
      <div>
        <Label htmlFor="previousVisaNumber">Previous Visa Number (if known)</Label>
        <Input 
          id="previousVisaNumber"
          value={formData.previousVisaNumber || ''}
          onChange={(e) => updateFormData({ previousVisaNumber: e.target.value })}
        />
      </div>
      
      <div>
        <Label htmlFor="previousVisaIssueDate">Issue Date (if known)</Label>
        <Input 
          id="previousVisaIssueDate"
          type="date"
          value={formData.previousVisaIssueDate || ''}
          onChange={(e) => updateFormData({ previousVisaIssueDate: e.target.value })}
        />
      </div>
      
      <div>
        <Label>Has your U.S. visa ever been lost or stolen?</Label>
        <RadioGroup 
          value={formData.visaLostOrStolen || ""}
          onValueChange={(value) => updateFormData({ visaLostOrStolen: value })}
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="yes" id="visaLostYes" />
            <Label htmlFor="visaLostYes">Yes</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="no" id="visaLostNo" />
            <Label htmlFor="visaLostNo">No</Label>
          </div>
        </RadioGroup>
      </div>
      
      <div>
        <Label>Has your U.S. visa ever been cancelled or revoked?</Label>
        <RadioGroup 
          value={formData.visaCancelledOrRevoked || ""}
          onValueChange={(value) => updateFormData({ visaCancelledOrRevoked: value })}
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="yes" id="visaCancelledYes" />
            <Label htmlFor="visaCancelledYes">Yes</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="no" id="visaCancelledNo" />
            <Label htmlFor="visaCancelledNo">No</Label>
          </div>
        </RadioGroup>
      </div>
      
      {(formData.visaLostOrStolen === 'yes' || formData.visaCancelledOrRevoked === 'yes') && (
        <div>
          <Label htmlFor="visaIssueExplanation">Please Explain</Label>
          <Textarea 
            id="visaIssueExplanation"
            value={formData.visaIssueExplanation || ''}
            onChange={(e) => updateFormData({ visaIssueExplanation: e.target.value })}
          />
        </div>
      )}
    </div>
  );
}

// Additional Information Step
function AdditionalInfoStep({ formData, updateFormData }: any) {
  return (
    <div className="space-y-4">
      <div>
        <Label>Are you traveling with someone else?</Label>
        <RadioGroup 
          value={formData.travelingWithOthers || ""}
          onValueChange={(value) => updateFormData({ travelingWithOthers: value })}
        >
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="yes" id="travelWithOthersYes" />
            <Label htmlFor="travelWithOthersYes">Yes</Label>
          </div>
          <div className="flex items-center space-x-2">
            <RadioGroupItem value="no" id="travelWithOthersNo" />
            <Label htmlFor="travelWithOthersNo">No</Label>
          </div>
        </RadioGroup>
      </div>
      
      {formData.travelingWithOthers === 'yes' && (
        <div>
          <Label htmlFor="travelCompanions">Please list the names of those traveling with you</Label>
          <Textarea 
            id="travelCompanions"
            value={formData.travelCompanions || ''}
            onChange={(e) => updateFormData({ travelCompanions: e.target.value })}
          />
        </div>
      )}
      
      <div>
        <Label htmlFor="usPOC">U.S. Point of Contact (Name, Address, Phone)</Label>
        <Textarea 
          id="usPOC"
          value={formData.usPOC || ''}
          onChange={(e) => updateFormData({ usPOC: e.target.value })}
        />
      </div>
      
      <div>
        <Label htmlFor="usAddressStaying">Address Where You Will Stay in the U.S.</Label>
        <Textarea 
          id="usAddressStaying"
          value={formData.usAddressStaying || ''}
          onChange={(e) => updateFormData({ usAddressStaying: e.target.value })}
        />
      </div>
      
      <div className="flex items-start space-x-2">
        <Checkbox 
          id="confirmInfo" 
          checked={formData.confirmInfo || false}
          onCheckedChange={(checked) => 
            updateFormData({ confirmInfo: checked === true ? true : false })
          }
        />
        <Label htmlFor="confirmInfo" className="text-sm">
          I confirm that the information provided is true and accurate to the best of my knowledge.
        </Label>
      </div>
    </div>
  );
}

// Review and Submit Step
function ReviewStep({ formData }: any) {
  return (
    <div className="space-y-4">
      <h3 className="text-lg font-medium">Review Your Information</h3>
      
      <div className="border rounded-md p-4 space-y-4">
        <div>
          <h4 className="font-medium">Personal Information</h4>
          <p>Name: {formData.firstName} {formData.lastName}</p>
          <p>Date of Birth: {formData.birthDate}</p>
          <p>Place of Birth: {formData.birthPlace}</p>
          <p>Nationality: {formData.nationality}</p>
        </div>
        
        <div>
          <h4 className="font-medium">Contact Information</h4>
          <p>Address: {formData.streetAddress}, {formData.city}, {formData.state}, {formData.postalCode}, {formData.country}</p>
          <p>Phone: {formData.phone}</p>
          <p>Email: {formData.email}</p>
        </div>
        
        <div>
          <h4 className="font-medium">Passport Information</h4>
          <p>Passport Number: {formData.passportNumber}</p>
          <p>Issue Date: {formData.passportIssueDate}</p>
          <p>Expiry Date: {formData.passportExpiryDate}</p>
          <p>Issuing Authority: {formData.passportIssuingAuthority}</p>
        </div>
        
        <div>
          <h4 className="font-medium">Travel Information</h4>
          <p>Purpose of Trip: {formData.purposeOfTrip === 'other' ? formData.purposeOfTripOther : formData.purposeOfTrip}</p>
          <p>Arrival Date: {formData.intendedArrivalDate}</p>
          <p>Length of Stay: {formData.intendedLengthOfStay}</p>
          <p>Previous U.S. Visit: {formData.previouslyVisitedUS === 'yes' ? 'Yes' : 'No'}</p>
          {formData.previouslyVisitedUS === 'yes' && (
            <>
              <p>Previous Visa Number: {formData.previousVisaNumber || 'Not provided'}</p>
              <p>Previous Visa Issue Date: {formData.previousVisaIssueDate || 'Not provided'}</p>
            </>
          )}
        </div>
        
        <div>
          <h4 className="font-medium">Additional Information</h4>
          <p>Traveling With Others: {formData.travelingWithOthers === 'yes' ? 'Yes' : 'No'}</p>
          {formData.travelingWithOthers === 'yes' && (
            <p>Travel Companions: {formData.travelCompanions}</p>
          )}
          <p>U.S. Point of Contact: {formData.usPOC}</p>
          <p>U.S. Address: {formData.usAddressStaying}</p>
        </div>
      </div>
      
      <p className="text-sm text-muted-foreground">
        Please review all information carefully before submitting. Once submitted, you may not be able to make changes.
      </p>
    </div>
  );
}

export function DS160Form() {
  const { user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  
  // Define the form steps with conditions
  const formSteps = [
    {
      id: 'personal-info',
      title: 'Personal Information',
      component: <PersonalInfoStep />
    },
    {
      id: 'contact-info',
      title: 'Contact Information',
      component: <ContactInfoStep />
    },
    {
      id: 'passport-info',
      title: 'Passport Information',
      component: <PassportInfoStep />
    },
    {
      id: 'travel-info',
      title: 'Travel Information',
      component: <TravelInfoStep />
    },
    {
      id: 'previous-visa',
      title: 'Previous Visa Information',
      component: <PreviousVisaStep />,
      condition: (formData: any) => formData.previouslyVisitedUS === 'yes'
    },
    {
      id: 'additional-info',
      title: 'Additional Information',
      component: <AdditionalInfoStep />
    },
    {
      id: 'review',
      title: 'Review and Submit',
      component: <ReviewStep />
    }
  ];
  
  const handleFormComplete = async (formData: Record<string, any>) => {
    if (!user) {
      toast({
        variant: "destructive",
        title: "Authentication Error",
        description: "You must be logged in to submit forms."
      });
      navigate('/auth');
      return;
    }
    
    try {
      // Generate a confirmation code
      const confirmationCode = `DS160-${Math.random().toString(36).substring(2, 10).toUpperCase()}`;
      
      // Create submission record
      const { data: submission, error: submissionError } = await supabase
        .from('submissions')
        .insert({
          user_id: user.id,
          status: 'completed',
          submitted_at: new Date().toISOString(),
          confirmation_code: confirmationCode,
          notes: JSON.stringify(formData)
        })
        .select()
        .single();
      
      if (submissionError) throw submissionError;
      
      // Redirect to success page or show success message
      navigate('/', { 
        state: { 
          success: true,
          message: `Form submitted successfully! Your confirmation code is ${confirmationCode}.`
        } 
      });
    } catch (error) {
      console.error('Error submitting form:', error);
      toast({
        variant: "destructive",
        title: "Submission Error",
        description: "There was an error submitting your form. Please try again."
      });
    }
  };
  
  return (
    <div className="container py-8">
      <h2 className="text-2xl font-bold mb-8 text-center">DS-160 Visa Application Form</h2>
      
      <MultiStepForm
        formSteps={formSteps}
        onComplete={handleFormComplete}
        formId="ds160"
      />
    </div>
  );
}

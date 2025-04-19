
import { useState, useEffect } from 'react';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { useToast } from '@/components/ui/use-toast';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Loader2, FileText, Clock, CheckCircle, XCircle } from 'lucide-react';

export function SubmissionHistory() {
  const { user } = useAuth();
  const [submissions, setSubmissions] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    if (user) {
      fetchSubmissions();
    }
  }, [user]);

  const fetchSubmissions = async () => {
    try {
      setLoading(true);
      const { data, error } = await supabase
        .from('submissions')
        .select(`
          *,
          documents:document_id (
            file_name,
            original_name
          )
        `)
        .eq('user_id', user?.id)
        .order('created_at', { ascending: false });
      
      if (error) throw error;
      setSubmissions(data || []);
    } catch (error) {
      console.error('Error fetching submissions:', error);
      toast({
        variant: "destructive",
        title: "Error",
        description: "Failed to load submission history",
      });
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-500">Completed</Badge>;
      case 'pending':
        return <Badge className="bg-yellow-500">Pending</Badge>;
      case 'processing':
        return <Badge className="bg-blue-500">Processing</Badge>;
      case 'failed':
        return <Badge className="bg-red-500">Failed</Badge>;
      default:
        return <Badge>{status}</Badge>;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'pending':
        return <Clock className="h-5 w-5 text-yellow-500" />;
      case 'processing':
        return <Loader2 className="h-5 w-5 text-blue-500 animate-spin" />;
      case 'failed':
        return <XCircle className="h-5 w-5 text-red-500" />;
      default:
        return <FileText className="h-5 w-5 text-gray-500" />;
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    );
  }

  if (submissions.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Submission History</CardTitle>
          <CardDescription>No submissions yet</CardDescription>
        </CardHeader>
        <CardContent className="text-center py-8 text-gray-500">
          <FileText className="h-12 w-12 mx-auto mb-4 text-gray-400" />
          <p>You haven't submitted any forms yet.</p>
          <p className="mt-2">When you submit a form, it will appear here.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Submission History</CardTitle>
        <CardDescription>Track your recent form submissions</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {submissions.map((submission) => (
            <div key={submission.id} className="flex items-center space-x-4 p-4 border rounded-lg">
              {getStatusIcon(submission.status)}
              <div className="flex-1">
                <div className="flex justify-between">
                  <h4 className="font-medium">
                    {submission.documents?.original_name || 'Document'}
                  </h4>
                  {getStatusBadge(submission.status)}
                </div>
                <div className="flex justify-between mt-1">
                  <p className="text-sm text-gray-500">
                    {submission.submitted_at 
                      ? new Date(submission.submitted_at).toLocaleString() 
                      : new Date(submission.created_at).toLocaleString()}
                  </p>
                  {submission.confirmation_code && (
                    <p className="text-sm font-mono">
                      Confirmation: {submission.confirmation_code}
                    </p>
                  )}
                </div>
              </div>
              <Button size="sm" variant="outline">Details</Button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

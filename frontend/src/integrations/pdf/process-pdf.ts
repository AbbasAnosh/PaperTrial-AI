import { NextApiRequest, NextApiResponse } from "next";
import { UnstructuredClient } from "@unstructured-io/sdk";
import { createClient } from "@supabase/supabase-js";

// Initialize Unstructured client
const unstructured = new UnstructuredClient({
  apiKey: process.env.UNSTRUCTURED_API_KEY || "",
});

// Initialize Supabase client
const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL || "",
  process.env.SUPABASE_SERVICE_ROLE_KEY || ""
);

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== "POST") {
    return res.status(405).json({ error: "Method not allowed" });
  }

  try {
    const file = req.body.file;
    if (!file) {
      return res.status(400).json({ error: "No file provided" });
    }

    // Process PDF with Unstructured.io
    const result = await unstructured.processPdf({
      file: file,
      strategy: "hi_res",
      output_format: "json",
    });

    // Extract fields from the processed PDF
    const extractedFields = extractFieldsFromPdf(result);

    // Store the processed data in Supabase
    const { data, error } = await supabase.from("processed_documents").insert([
      {
        original_filename: file.name,
        processed_data: extractedFields,
        user_id: req.user?.id, // Assuming you have user authentication
      },
    ]);

    if (error) {
      throw error;
    }

    return res.status(200).json({
      success: true,
      data: extractedFields,
    });
  } catch (error) {
    console.error("Error processing PDF:", error);
    return res.status(500).json({ error: "Failed to process PDF" });
  }
}

function extractFieldsFromPdf(pdfData: any) {
  // This is a placeholder function that should be customized based on your specific form types
  // You'll need to implement logic to identify and extract relevant fields from the PDF data

  const fields: Record<string, any> = {};

  // Example extraction logic (customize based on your needs):
  pdfData.elements.forEach((element: any) => {
    // Look for form fields based on text patterns, positions, etc.
    if (element.text.includes("Name:")) {
      fields.name = element.text.replace("Name:", "").trim();
    }
    // Add more field extraction logic here
  });

  return fields;
}

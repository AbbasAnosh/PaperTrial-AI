"""
Test script for form template and mapping workflow.
This script demonstrates the complete workflow from creating a form template
to processing a PDF and mapping fields.
"""

import asyncio
import os
from app.services.form_service import FormService
from app.services.mapping_service import MappingService
from app.services.pdf_processor import PDFProcessor
from app.models.form_template import FormTemplate, FormField
from app.models.form_submission import FormSubmission
from app.core.config import settings
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_form_workflow():
    """Test the complete form template and mapping workflow"""
    try:
        # Initialize services
        form_service = FormService()
        mapping_service = MappingService()
        pdf_processor = PDFProcessor()

        # Create a sample form template
        template = FormTemplate(
            name="Sample Tax Form",
            description="A sample tax form for testing",
            fields=[
                FormField(
                    name="full_name",
                    label="Full Name",
                    field_type="text",
                    required=True
                ),
                FormField(
                    name="tax_id",
                    label="Tax ID",
                    field_type="text",
                    required=True
                ),
                FormField(
                    name="income",
                    label="Annual Income",
                    field_type="number",
                    required=True
                )
            ]
        )

        # Save the template
        saved_template = await form_service.create_template(template)
        logger.info(f"Created template: {saved_template.name}")

        # Process a sample PDF
        pdf_path = "path/to/your/sample.pdf"  # Replace with actual PDF path
        if not os.path.exists(pdf_path):
            logger.error(f"PDF file not found: {pdf_path}")
            return

        # Process PDF and extract fields
        extracted_data = await pdf_processor.process_pdf(pdf_path)
        logger.info(f"Extracted {len(extracted_data['fields'])} fields from PDF")

        # Create field mappings
        mappings = []
        for field in saved_template.fields:
            # Find the best matching extracted field
            best_match = None
            highest_similarity = 0

            for extracted_field in extracted_data['fields']:
                similarity = mapping_service._calculate_similarity(
                    field.label.lower(),
                    extracted_field['label'].lower()
                )
                if similarity > highest_similarity and similarity > 0.7:
                    highest_similarity = similarity
                    best_match = extracted_field

            if best_match:
                mappings.append({
                    'template_field': field.name,
                    'extracted_field': best_match['label'],
                    'confidence': highest_similarity
                })

        # Create a form submission
        submission = FormSubmission(
            template_id=saved_template.id,
            status="draft",
            field_values={
                mapping['template_field']: extracted_data['fields'][mapping['extracted_field']]['value']
                for mapping in mappings
            }
        )

        # Save the submission
        saved_submission = await form_service.create_submission(submission)
        logger.info(f"Created submission: {saved_submission.id}")

        # Clean up
        await pdf_processor.cleanup()
        logger.info("Test completed successfully")

    except Exception as e:
        logger.error(f"Error in test workflow: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(test_form_workflow()) 
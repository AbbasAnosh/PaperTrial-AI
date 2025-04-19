import { FormField, FormType } from "@/types/form";
import Fuse from "fuse.js";

interface PdfElement {
  text: string;
  type: string;
  coordinates: {
    x: number;
    y: number;
  };
  confidence_score?: number;
  cluster?: number;
  related_fields?: string[];
}

interface FieldExtractionRule {
  pattern: RegExp;
  fieldName: string;
  transform?: (value: string) => string;
  validationRules?: {
    required?: boolean;
    pattern?: RegExp;
    minLength?: number;
    maxLength?: number;
  };
}

interface FieldMapping {
  pdfField: string;
  userField: string;
  confidence: number;
  lastUsed: Date;
  frequency: number;
}

export class FieldExtractor {
  private formType: FormType;
  private extractionRules: Record<FormType, FieldExtractionRule[]>;
  private mappingHistory: FieldMapping[] = [];
  private fuzzyMatcher: Fuse<FieldMapping>;

  constructor(formType: FormType) {
    this.formType = formType;
    this.extractionRules = {
      DS160: this.getDS160Rules(),
      EIN: this.getEINRules(),
      // Add more form types here
    };
    this.fuzzyMatcher = new Fuse(this.mappingHistory, {
      keys: ["pdfField", "userField"],
      threshold: 0.3,
    });
  }

  private getDS160Rules(): FieldExtractionRule[] {
    return [
      {
        pattern: /Name:\s*([^\n]+)/i,
        fieldName: "name",
        transform: (value) => value.trim(),
      },
      {
        pattern: /Date of Birth:\s*([^\n]+)/i,
        fieldName: "dateOfBirth",
        transform: (value) => this.parseDate(value),
      },
      {
        pattern: /Passport Number:\s*([^\n]+)/i,
        fieldName: "passportNumber",
      },
      // Add more DS-160 specific rules
    ];
  }

  private getEINRules(): FieldExtractionRule[] {
    return [
      {
        pattern: /Legal Name:\s*([^\n]+)/i,
        fieldName: "legalName",
      },
      {
        pattern: /Business Name:\s*([^\n]+)/i,
        fieldName: "businessName",
      },
      {
        pattern: /Taxpayer ID:\s*([^\n]+)/i,
        fieldName: "taxpayerId",
      },
      // Add more EIN specific rules
    ];
  }

  public extractFields(pdfElements: PdfElement[]): FormField[] {
    const fields: FormField[] = [];
    const rules = this.extractionRules[this.formType];

    pdfElements.forEach((element) => {
      rules.forEach((rule) => {
        const match = element.text.match(rule.pattern);
        if (match) {
          let value = match[1];
          if (rule.transform) {
            value = rule.transform(value);
          }

          const field: FormField = {
            name: rule.fieldName,
            value: value,
            type: this.determineFieldType(rule.fieldName),
            required: rule.validationRules?.required ?? true,
            coordinates: element.coordinates,
            confidence: element.confidence_score,
            cluster: element.cluster,
            relatedFields: element.related_fields,
            validationRules: rule.validationRules,
          };

          // Try to find a mapping for this field
          const mapping = this.findBestMapping(field.name);
          if (mapping) {
            field.mappedTo = mapping.userField;
            field.mappingConfidence = mapping.confidence;
          }

          fields.push(field);
        }
      });
    });

    return this.postProcessFields(fields);
  }

  private findBestMapping(fieldName: string): FieldMapping | null {
    // Try exact match first
    const exactMatch = this.mappingHistory.find(
      (m) => m.pdfField === fieldName
    );
    if (exactMatch) {
      return exactMatch;
    }

    // Try fuzzy match
    const fuzzyMatches = this.fuzzyMatcher.search(fieldName);
    if (fuzzyMatches.length > 0) {
      // Sort by frequency and confidence
      const bestMatch = fuzzyMatches.reduce((best, current) => {
        const score = current.item.frequency * current.item.confidence;
        const bestScore = best ? best.frequency * best.confidence : 0;
        return score > bestScore ? current.item : best;
      }, null as FieldMapping | null);

      return bestMatch;
    }

    return null;
  }

  private postProcessFields(fields: FormField[]): FormField[] {
    // Group fields by cluster
    const clusters = new Map<number, FormField[]>();
    fields.forEach((field) => {
      if (field.cluster !== undefined && field.cluster !== -1) {
        if (!clusters.has(field.cluster)) {
          clusters.set(field.cluster, []);
        }
        clusters.get(field.cluster)?.push(field);
      }
    });

    // Process each cluster
    clusters.forEach((clusterFields) => {
      // Find the field with highest confidence in cluster
      const bestField = clusterFields.reduce((best, current) =>
        (current.confidence || 0) > (best.confidence || 0) ? current : best
      );

      // Enhance related fields with best field's information
      clusterFields.forEach((field) => {
        if (field !== bestField) {
          field.relatedTo = bestField.name;
          field.inheritedConfidence = bestField.confidence;
        }
      });
    });

    return fields;
  }

  public updateMapping(pdfField: string, userField: string, success: boolean) {
    const existingMapping = this.mappingHistory.find(
      (m) => m.pdfField === pdfField
    );

    if (existingMapping) {
      existingMapping.frequency++;
      existingMapping.lastUsed = new Date();
      existingMapping.confidence = this.calculateMappingConfidence(
        existingMapping,
        success
      );
    } else {
      this.mappingHistory.push({
        pdfField,
        userField,
        confidence: success ? 0.8 : 0.4,
        lastUsed: new Date(),
        frequency: 1,
      });
    }

    // Update fuzzy matcher with new data
    this.fuzzyMatcher = new Fuse(this.mappingHistory, {
      keys: ["pdfField", "userField"],
      threshold: 0.3,
    });
  }

  private calculateMappingConfidence(
    mapping: FieldMapping,
    success: boolean
  ): number {
    const baseConfidence = mapping.confidence;
    const frequencyBonus = Math.min(mapping.frequency / 10, 0.3);
    const successFactor = success ? 0.1 : -0.2;

    return Math.max(
      0.1,
      Math.min(1, baseConfidence + frequencyBonus + successFactor)
    );
  }

  private determineFieldType(fieldName: string): string {
    // Enhanced type detection with common patterns
    const typePatterns = {
      date: /(date|dob|birth|expiry|expiration)/i,
      email: /(email|e-mail)/i,
      phone: /(phone|telephone|mobile|cell)/i,
      number: /(number|amount|quantity|count)/i,
      currency: /(price|cost|fee|payment|$)/i,
      checkbox: /(agree|accept|confirm|check)/i,
      textarea: /(description|comments|notes|address)/i,
    };

    for (const [type, pattern] of Object.entries(typePatterns)) {
      if (pattern.test(fieldName)) {
        return type;
      }
    }

    return "text";
  }

  private parseDate(dateStr: string): string {
    // Implement date parsing logic
    // This is a simple implementation - you might want to use a library like date-fns
    try {
      return new Date(dateStr).toISOString().split("T")[0];
    } catch {
      return dateStr;
    }
  }
}

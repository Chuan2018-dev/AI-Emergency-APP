class ReportItem {
  final int id;
  final String emergencyType;
  final String description;
  final String status;
  final String createdAt;
  final String severityLabel;
  final double verificationScore;

  ReportItem({
    required this.id,
    required this.emergencyType,
    required this.description,
    required this.status,
    required this.createdAt,
    required this.severityLabel,
    required this.verificationScore,
  });

  factory ReportItem.fromJson(Map<String, dynamic> json) => ReportItem(
        id: json['id'],
        emergencyType: json['emergency_type'],
        description: json['description'],
        status: json['status'],
        createdAt: json['created_at'],
        severityLabel: json['severity_label'] ?? 'Low',
        verificationScore: (json['verification_score'] ?? 0).toDouble(),
      );
}

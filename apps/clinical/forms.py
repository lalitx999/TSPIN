"""
Forms for 39 Biological Axes Evaluation (Pillars 2, 3).
"""

from django import forms
from clinical.models import BiologicalRecord, AnalysisRecord

class BiologicalRecordForm(forms.ModelForm):
    """
    ฟอร์มบันทึกและปรับจูนคะแนน 39 แกนชีววิทยาโดยแพทย์
    """
    class Meta:
        model = BiologicalRecord
        fields = ['is_baseline', 'notes'] + [f'axis_{i}' for i in range(1, 40)]
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'ระบุบันทึกความเห็นทางคลินิก สมมติฐาน หรือข้อสังเกตเพิ่มเติมของแพทย์'
            }),
            'is_baseline': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # ตั้งค่า class สำหรับช่องคะแนน 39 แกนให้เป็นตัวเลข 0 - 100
        for i in range(1, 40):
            field_name = f'axis_{i}'
            if field_name in self.fields:
                self.fields[field_name].widget.attrs.update({
                    'class': 'form-control form-control-sm text-center font-mono font-weight-bold axis-score-input',
                    'min': '0',
                    'max': '100',
                    'type': 'number'
                })


class AnalysisApprovalForm(forms.ModelForm):
    """
    ฟอร์มอนุมัติผลการวิเคราะห์และออกรายงานทางคลินิก (Physician Sign-off Gate)
    """
    class Meta:
        model = AnalysisRecord
        fields = ['status', 'doctor_summary']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-control'}),
            'doctor_summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'ระบุบทสรุปทางการแพทย์และการวินิจฉัยเชิงกลไกสำหรับคนไข้รายนี้'
            }),
        }

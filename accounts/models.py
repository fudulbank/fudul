from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    user = models.OneToOneField(User, verbose_name="مستخدمـ/ـة")
    ar_first_name = models.CharField('الاسم الأول', max_length=30)
    ar_middle_name = models.CharField('الاسم الأوسط', max_length=30)
    ar_last_name = models.CharField('الاسم الأخير', max_length=30)
    en_first_name = models.CharField('الاسم الأول', max_length=30)
    en_middle_name = models.CharField('الاسم الأوسط', max_length=30)
    en_last_name = models.CharField(u'الاسم الأخير', max_length=30)
    college = models.ForeignKey('College', verbose_name="الكلية", null=True)
    mobile_number = models.CharField("رقم الجوال", max_length=14)
    submission_date = models.DateTimeField("تاريخ التسجيل", auto_now_add=True)
    modification_date = models.DateTimeField("تاريخ التعديل", auto_now=True, null=True)

    def __str__(self):
        return self.user.username

    def get_ar_full_name(self):
        ar_fullname = None
        try:
            # If the Arabic first name is missing, let's assume the
            # rest is also missing.
            if self.ar_first_name:
                ar_fullname = " ".join([self.ar_first_name,
                                        self.ar_middle_name,
                                        self.ar_last_name])
        except AttributeError: # If the user has their details missing
            pass

        return ar_fullname

    def get_en_full_name(self):
        en_fullname = None
        try:
            # If the English first name is missing, let's assume the
            # rest is also missing.
            if self.en_first_name:
                en_fullname = " ".join([self.en_first_name,
                                        self.en_middle_name,
                                        self.en_last_name])
        except AttributeError: # If the user has their details missing
            pass

        return en_fullname

class College(models.Model):
    name = models.CharField("الاسم", max_length=50)
    institution = models.ForeignKey('Institution',
                                    verbose_name="المؤسسة")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "كلية"
        verbose_name_plural = "الكليات"

class Institution(models.Model):
    name = models.CharField("الاسم", max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "مؤسسة"
        verbose_name_plural = "المؤسسات"

from django.db import models


class Employee(models.Model):
    MARITAL_STATUS_CHOICES = [
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
    ]
    
    SEX_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    CIVILIAN_OR_EX_SERVICEMAN_CHOICES = [
        ('civilian', 'Civilian'),
        ('ex_serviceman', 'Ex Serviceman'),
    ]

    POLICE_VERIFICATION_CHOICES = [
        ('yes', 'Yes'),
        ('applied', 'Applied'),
        ('no', 'No'),
    ]

    POST_APPLIED_FOR_CHOICES = [
        ('Security Guard', 'Security Guard'),
        ('Lady Searcher', 'Lady Searcher'),
        ('Head Guard', 'Head Guard'),
        ('Supervisor', 'Supervisor'),
        ('Assistant Security Officer', 'Assistant Security Officer'),
        ('Security Officer', 'Security Officer'),
        ('Chief Security Officer', 'Chief Security Officer'),
        ('Area Officer', 'Area Officer'),
        ('Territory Manager', 'Territory Manager'),
        ('Training Officer', 'Training Officer'),
        ('Night Rounder', 'Night Rounder'),
        ('Patrol Officer', 'Patrol Officer'),
        ('Gunman', 'Gunman'),
        ('Driver', 'Driver'),
        ('Protection Officer', 'Protection Officer'),
        ('Concierge', 'Concierge'),
        ('CCTV Operator', 'CCTV Operator'),
        ('Staff', 'Staff'),
        ('House Keeping', 'House Keeping'),
    ]
    
    APPROVAL_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]

    RELIGION_CHOICES = [
        ('hindu', 'Hindu'),
        ('muslim', 'Muslim'),
        ('christian', 'Christian'),
        ('sikh', 'Sikh'),
        ('buddhist', 'Buddhist'),
        ('jain', 'Jain'),
        ('parsi', 'Parsi'),
    ]

    NATIONALITY_CHOICES = [
        ('indian', 'Indian'),
        ('nepali', 'Nepali'),
    ]

    STATE_CHOICES = [
        # States
        ('andhra_pradesh', 'Andhra Pradesh'),
        ('arunachal_pradesh', 'Arunachal Pradesh'),
        ('assam', 'Assam'),
        ('bihar', 'Bihar'),
        ('chhattisgarh', 'Chhattisgarh'),
        ('goa', 'Goa'),
        ('gujarat', 'Gujarat'),
        ('haryana', 'Haryana'),
        ('himachal_pradesh', 'Himachal Pradesh'),
        ('jharkhand', 'Jharkhand'),
        ('karnataka', 'Karnataka'),
        ('kerala', 'Kerala'),
        ('madhya_pradesh', 'Madhya Pradesh'),
        ('maharashtra', 'Maharashtra'),
        ('manipur', 'Manipur'),
        ('meghalaya', 'Meghalaya'),
        ('mizoram', 'Mizoram'),
        ('nagaland', 'Nagaland'),
        ('odisha', 'Odisha'),
        ('punjab', 'Punjab'),
        ('rajasthan', 'Rajasthan'),
        ('sikkim', 'Sikkim'),
        ('tamil_nadu', 'Tamil Nadu'),
        ('telangana', 'Telangana'),
        ('tripura', 'Tripura'),
        ('uttar_pradesh', 'Uttar Pradesh'),
        ('uttarakhand', 'Uttarakhand'),
        ('west_bengal', 'West Bengal'),

        # Union Territories
        ('andaman_nicobar', 'Andaman and Nicobar Islands'),
        ('chandigarh', 'Chandigarh'),
        ('dadra_nagar_haveli_daman_diu', 'Dadra and Nagar Haveli and Daman and Diu'),
        ('delhi', 'Delhi'),
        ('jammu_kashmir', 'Jammu and Kashmir'),
        ('ladakh', 'Ladakh'),
        ('lakshadweep', 'Lakshadweep'),
        ('puducherry', 'Puducherry'),
    ]

    SALUTATION_CHOICES = [
        ('mr', 'Mr.'),
        ('mrs', 'Mrs.'),
        ('ms', 'Ms.'),
        ('miss', 'Miss'),
        ('dr', 'Dr.'),
        ('prof', 'Prof.'),
        ('rev', 'Rev.'),
        ('sir', 'Sir'),
        ('madam', 'Madam'),
        ('mx', 'Mx.'),
        ('capt', 'Capt.'),
        ('col', 'Col.'),
        ('lt', 'Lt.'),
        ('maj', 'Maj.'),
        ('gen', 'Gen.'),
        ('hon', 'Hon.'),
        ('fr', 'Fr.'),
    ]


    # Basic Information
    salutation = models.CharField(max_length=50, choices=SALUTATION_CHOICES)
    post_applied_for = models.CharField(max_length=50, choices=POST_APPLIED_FOR_CHOICES)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    surname = models.CharField(max_length=100)
    full_name = models.CharField(max_length=100)
    height = models.DecimalField(max_digits=5, decimal_places=2, help_text="In cm")
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="In kg")
    religion = models.CharField(max_length=50, choices=RELIGION_CHOICES)
    nationality = models.CharField(max_length=50, choices=NATIONALITY_CHOICES)
    date_of_birth = models.DateField()
    date_of_joining = models.DateField()
    sex = models.CharField(max_length=10, choices=SEX_CHOICES)
    marital_status = models.CharField(max_length=10, choices=MARITAL_STATUS_CHOICES)
    birth_place = models.CharField(max_length=100)
    local_address = models.TextField()
    pincode = models.CharField(max_length=10)
    mobile = models.CharField(max_length=15)
    email = models.EmailField()
    civilian_or_ex_serviceman = models.CharField(max_length=20, choices=CIVILIAN_OR_EX_SERVICEMAN_CHOICES)
    identification_mark = models.CharField(max_length=255)
    conviction_details = models.TextField(blank=True, null=True)
    photo = models.ImageField(upload_to='employee_photos/', blank=True, null=True)
    
    # Qualification & Documents
    educational_qualification = models.TextField()
    # english_fluency = models.IntegerField(choices=[(i, i) for i in range(6)])  # 0-5 scale
    police_verification = models.CharField(max_length=10, choices=POLICE_VERIFICATION_CHOICES, default='applied')
    # previous_experience = models.TextField(blank=True, null=True)
    aadhar_no = models.CharField(max_length=12)
    pan_card_no = models.CharField(max_length=10)
    ration_card = models.CharField(max_length=50, blank=True, null=True)
    affidavit = models.CharField(max_length=50, blank=True, null=True)
    
    # Gun License Details
    gun_license_no = models.CharField(max_length=50, blank=True, null=True)
    gun_uin_no = models.CharField(max_length=50, blank=True, null=True)
    gun_registration = models.CharField(max_length=50, blank=True, null=True)
    gun_issue_place = models.CharField(max_length=100, blank=True, null=True)
    gun_issue_authority = models.CharField(max_length=100, blank=True, null=True)
    gun_license_expiry = models.DateField(blank=True, null=True)
    
    # Experience Details
    experience_details = models.TextField(blank=True, null=True)
    
    # Emergency Contact Information
    emergency_contact_name = models.CharField(max_length=100)
    emergency_contact_relationship = models.CharField(max_length=50)
    emergency_contact_phone = models.CharField(max_length=15)
    emergency_contact_pin = models.CharField(max_length=10)
    emergency_contact_address = models.TextField()
    emergency_contact_directions = models.TextField(blank=True, null=True)
    
    # Family Information
    mother_name = models.CharField(max_length=100, blank=True, null=True)
    father_name = models.CharField(max_length=100, blank=True, null=True)
    children_details = models.TextField(blank=True, null=True)
    spouse_name = models.CharField(max_length=100, blank=True, null=True)
    relatives_details = models.TextField(blank=True, null=True)
    
    # Hometown Details
    village = models.CharField(max_length=100, blank=True, null=True)
    tehsil = models.CharField(max_length=100, blank=True, null=True)
    district = models.CharField(max_length=100, blank=True, null=True)
    post_office = models.CharField(max_length=100, blank=True, null=True)
    police_station = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=50, choices=STATE_CHOICES)
    hometown_pin_code = models.CharField(max_length=10, blank=True, null=True)
    hometown_phone = models.CharField(max_length=15, blank=True, null=True)
    hometown_directions = models.TextField(blank=True, null=True)
    has_experience = models.BooleanField(default=False, help_text="Check if the employee has prior experience")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    approval_status = models.CharField(max_length=20, choices=APPROVAL_STATUS_CHOICES, default='pending')
    remarks = models.TextField(blank=True, null=True)
    class Meta:
        db_table = 'employees'

    def __str__(self):
        return f"{self.first_name} {self.surname}"
   
class Reference(models.Model):
    employee = models.ForeignKey(Employee, related_name='references', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    relationship = models.CharField(max_length=50)
    time_known = models.CharField(max_length=50)
    occupation = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.TextField()
    directions = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'references'
    
    def __str__(self):
        return f"Reference for {self.employee}: {self.name}"
    
class Experience(models.Model):
    employee = models.ForeignKey(Employee, related_name='experiences', on_delete=models.CASCADE)
    company_name = models.CharField(max_length=100)
    designation = models.CharField(max_length=100)
    salary = models.DecimalField(max_digits=10, decimal_places=2, help_text="In INR")
    address = models.TextField()
    years_of_experience = models.DecimalField(max_digits=4, decimal_places=1, help_text="In years")

    class Meta:
        db_table = 'experiences'

    def __str__(self):
        return f"{self.designation} at {self.company_name} for {self.employee}"
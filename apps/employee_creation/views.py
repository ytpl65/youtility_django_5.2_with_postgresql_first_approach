from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
import random
import string
from .models import Employee, Reference, Experience
from .forms import EmployeeForm, ReferenceFormSet, ExperienceFormSet

otp_storage = {}

def generate_otp(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_otp_email(email, otp):
    subject = 'Your OTP for Employee Creation Verification'
    message = f'Your OTP is: {otp}\nValid for 5 minutes.'
    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [email]
    try:
        send_mail(subject, message, from_email, recipient_list, fail_silently=False)
        return True
    except Exception as e:
        return str(e)

def employee_create(request):
    if request.method == 'POST':
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            action = request.POST.get('action')

            if action == 'request_otp':
                employee_form = EmployeeForm(request.POST, request.FILES)
                reference_formset = ReferenceFormSet(request.POST)
                experience_formset = ExperienceFormSet(request.POST)

                if employee_form.is_valid() and reference_formset.is_valid() and experience_formset.is_valid():
                    email = employee_form.cleaned_data['email']
                    otp = generate_otp()
                    otp_storage[email] = otp
                    email_result = send_otp_email(email, otp)
                    if email_result is True:
                        return JsonResponse({
                            'status': 'success',
                            'message': 'OTP sent to your email. Please verify.',
                        })
                    else:
                        return JsonResponse({
                            'status': 'error',
                            'message': f'Failed to send OTP: {email_result}',
                        }, status=500)
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Form validation failed',
                        'errors': {
                            'employee_errors': employee_form.errors.as_json(),
                            'reference_errors': [form.errors.as_json() for form in reference_formset.forms],
                            'experience_errors': [form.errors.as_json() for form in experience_formset.forms],
                        }
                    }, status=400)

            elif action == 'verify_otp':
                email = request.POST.get('email')
                user_otp = request.POST.get('otp')
                stored_otp = otp_storage.get(email)

                if stored_otp and user_otp == stored_otp:
                    employee_form = EmployeeForm(request.POST, request.FILES)
                    reference_formset = ReferenceFormSet(request.POST)
                    experience_formset = ExperienceFormSet(request.POST)

                    if employee_form.is_valid() and reference_formset.is_valid() and experience_formset.is_valid():
                        employee = employee_form.save()
                        references = reference_formset.save(commit=False)
                        for reference in references:
                            reference.employee = employee
                            reference.save()
                        experiences = experience_formset.save(commit=False)
                        for experience in experiences:
                            experience.employee = employee
                            experience.save()
                        for obj in experience_formset.deleted_objects:
                            obj.delete()
                        del otp_storage[email]
                        return JsonResponse({
                            'status': 'success',
                            'message': 'Employee and references created successfully',
                            'redirect_url': reverse('employee_creation:employee_list')
                        })
                    else:
                        return JsonResponse({
                            'status': 'error',
                            'message': 'Form validation failed after OTP verification',
                            'errors': {
                                'employee_errors': employee_form.errors.as_json(),
                                'reference_errors': [form.errors.as_json() for form in reference_formset.forms],
                                'experience_errors': [form.errors.as_json() for form in experience_formset.forms],
                            }
                        }, status=400)
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Invalid or expired OTP. Please request a new one.'
                    }, status=400)
        
        return JsonResponse({
            'status': 'error',
            'message': 'Invalid request method or action.'
        }, status=400)

    employee_form = EmployeeForm()
    reference_formset = ReferenceFormSet()
    experience_formset = ExperienceFormSet()
    return render(request, 'employee_creation/employee_form.html', {
        'form': employee_form,
        'reference_formset': reference_formset,
        'experience_formset': experience_formset,
    })

def employee_list(request):
    if request.GET.get('action') == 'list':
        return JsonResponse({
            'data': list(Employee.objects.filter(approval_status='pending').values())
        })
    return render(request, 'employee_creation/employee_list.html')
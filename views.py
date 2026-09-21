from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import generic
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from .models import Course, Enrollment, Question, Choice, Submission


def registration_request(request):
    context = {}
    if request.method == 'GET':
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    username = request.POST['username']
    password = request.POST['psw']
    first_name = request.POST['firstname']
    last_name = request.POST['lastname']
    if User.objects.filter(username=username).exists():
        context['message'] = "User already exists."
        return render(request, 'onlinecourse/user_registration_bootstrap.html', context)
    user = User.objects.create_user(username=username, first_name=first_name,
                                    last_name=last_name, password=password)
    login(request, user)
    return redirect("onlinecourse:index")


def login_request(request):
    context = {}
    if request.method == "POST":
        user = authenticate(username=request.POST['username'], password=request.POST['psw'])
        if user is not None:
            login(request, user)
            return redirect('onlinecourse:index')
        context['message'] = "Invalid username or password."
    return render(request, 'onlinecourse/user_login_bootstrap.html', context)


def logout_request(request):
    logout(request)
    return redirect('onlinecourse:index')


def check_if_enrolled(user, course):
    if user.id is not None:
        return Enrollment.objects.filter(user=user, course=course).exists()
    return False


class CourseListView(generic.ListView):
    template_name = 'onlinecourse/course_list_bootstrap.html'
    context_object_name = 'course_list'

    def get_queryset(self):
        user = self.request.user
        courses = Course.objects.order_by('-total_enrollment')[:10]
        for course in courses:
            if user.is_authenticated:
                course.is_enrolled = check_if_enrolled(user, course)
        return courses


class CourseDetailView(generic.DetailView):
    model = Course
    template_name = 'onlinecourse/course_details_bootstrap.html'


def enroll(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    if user.is_authenticated and not check_if_enrolled(user, course):
        Enrollment.objects.create(user=user, course=course, mode='honor')
        course.total_enrollment += 1
        course.save()
    return HttpResponseRedirect(reverse(viewname='onlinecourse:course_details', args=(course.id,)))


def extract_answers(request):
    submitted_answers = []
    for key in request.POST:
        if key.startswith('choice'):
            submitted_answers.append(int(request.POST[key]))
    return submitted_answers


def submit(request, course_id):
    course = get_object_or_404(Course, pk=course_id)
    user = request.user
    enrollment = Enrollment.objects.get(user=user, course=course)
    submission = Submission.objects.create(enrollment=enrollment)
    choices = extract_answers(request)
    submission.choices.set(choices)
    return HttpResponseRedirect(reverse(viewname='onlinecourse:exam_result',
                                        args=(course.id, submission.id)))


def show_exam_result(request, course_id, submission_id):
    course = get_object_or_404(Course, pk=course_id)
    submission = get_object_or_404(Submission, pk=submission_id)
    selected_ids = [c.id for c in submission.choices.all()]
    total_score = 0
    max_score = 0
    for question in course.question_set.all():
        max_score += question.grade
        if question.is_get_score(selected_ids):
            total_score += question.grade
    grade = int(total_score / max_score * 100) if max_score else 0
    context = {
        'course': course,
        'selected_ids': selected_ids,
        'grade': grade,
        'total_score': total_score,
        'max_score': max_score,
        'passed': grade >= 80,
    }
    return render(request, 'onlinecourse/exam_result_bootstrap.html', context)

from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def study(request):
    return render(request, "learning/study.html")


@login_required
def results(request):
    return render(request, "learning/results.html")

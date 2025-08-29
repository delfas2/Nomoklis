from django.shortcuts import render


def index(request):
    return render(request, 'nomoklis_app/index.html')
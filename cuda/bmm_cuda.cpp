#include <torch/extension.h>

#include <vector>

// CUDA forward declarations

int bmm_cuda_forward(
    std::vector<torch::Tensor> A,
    std::vector<torch::Tensor> B,
    std::vector<torch::Tensor> C,
    int* m,
    int* n,
    int* k);


// C++ interface

// NOTE: AT_ASSERT has become AT_CHECK on master after 0.4.
#define CHECK_CUDA(x) AT_ASSERTM(x.type().is_cuda(), #x " must be a CUDA tensor")
#define CHECK_CONTIGUOUS(x) AT_ASSERTM(x.is_contiguous(), #x " must be contiguous")
#define CHECK_INPUT(x) CHECK_CUDA(x); CHECK_CONTIGUOUS(x)

int bmm_forward(
    std::vector<torch::Tensor> A,
    std::vector<torch::Tensor> B,
    std::vector<torch::Tensor> C,
    torch::Tensor m, torch::Tensor n, torch::Tensor k) {
    double *pA = (double *) A[0].data_ptr();
    double *pB = (double *) B[0].data_ptr();

    std::cout<<"elements in A: "<<A.size()<<"\n";
    std::cout<<"elements in B: "<<B.size()<<"\n";

    // int* m_arr = (int*) malloc (2*sizeof(int));
    // int* n_arr = (int*) malloc (2*sizeof(int));
    // int* k_arr = (int*) malloc (2*sizeof(int));

    

    // for (int i = 0; i < A.size(); ++i)
    // {
    	
    // }

    int* m_arr = (int*) m.data_ptr();
    int* n_arr = (int*) n.data_ptr();
    int* k_arr = (int*) k.data_ptr();
    std::cout<<"here\n";
    std::cout<<m_arr[0]<<" "<<n_arr[0]<<" "<<k_arr[0]<<"\n";
    std::cout<<"finsihing arrays print\n";

  // CHECK_INPUT(A);
  // CHECK_INPUT(B);


  return bmm_cuda_forward(A, B, C, m_arr ,n_arr , k_arr);
}



PYBIND11_MODULE(TORCH_EXTENSION_NAME, m) {
  m.def("forward", &bmm_forward, "BMM forward (CUDA)");
}
